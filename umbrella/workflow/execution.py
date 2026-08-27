"""
Pipeline Execution Engine

This module contains the core execution logic for running processing pipelines.
It handles:
- Building execution context from database models
- Finding input data via PipeJoints
- Submitting jobs to SLURM
- Tracking execution state
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.utils import timezone
from processes.models import (
    JobLog,
    PipeExecution,
    PipeInPlan,
    PipeJoint,
    ProcRun,
    RunPipeData,
)
from processes.services.cluster_resolver import get_default_cluster_id
from umbrella_logger import logger

from .agent import RemoteJobSubmitter
from .context import RunContext
from .processors import BaseProcessor, get_processor


class ValidationError(Exception):
    """Raised when parameter validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {'; '.join(errors)}")


class PipelineExecutor:
    """
    Executes individual pipeline steps.

    Handles the full lifecycle of step execution:
    1. Build execution context from database
    2. Get and validate processor
    3. Validate parameters
    4. Render script
    5. Submit to SLURM
    6. Create execution records
    """

    def execute_pipe(
        self,
        pipe_in_plan: PipeInPlan,
        proc_run: ProcRun,
        user: User,
        parameters: Dict[str, Any],
        auth: Dict[str, str],
        cluster_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single pipe in a plan.

        Args:
            pipe_in_plan: The pipe instance to execute
            proc_run: The processing run this belongs to
            user: User executing the pipeline
            parameters: User-provided parameters
            auth: Cluster authentication (username/password or key)
            cluster_id: Optional cluster ID override (validates against allowed_clusters)

        Returns:
            Dict with execution info:
            {
                'job_id': str - SLURM job ID,
                'script_path': str - Path to uploaded script,
                'status': 'submitted',
                'pipe_execution_id': int - PipeExecution record ID
            }

        Raises:
            ValidationError: If parameters are invalid or cluster not allowed
            ValueError: If dependencies not met or processor not found
            Exception: If job submission fails
        """
        logger.info(
            f"Executing pipe {pipe_in_plan.pipe.name} for run {proc_run.name} (user: {user})",
        )

        # 1. Get processor for this pipe's software
        software = pipe_in_plan.pipe.software
        try:
            processor = get_processor(software.processor_class)
        except ValueError as e:
            raise ValueError(
                f"Cannot execute pipe {pipe_in_plan.pipe.name}: {e}. "
                f"Software '{software.name}' may not have a registered processor.",
            )

        # 2. Validate cluster selection
        if cluster_id:
            # Check if cluster is allowed for this software
            allowed = software.allowed_clusters if software.allowed_clusters else ["czii", "bruno"]
            if cluster_id not in allowed:
                raise ValidationError(
                    [
                        f"Cluster '{cluster_id}' is not allowed for software '{software.name}'. "
                        f"Allowed clusters: {', '.join(allowed)}",
                    ]
                )

        # 3. Build RunContext with inputs from previous pipes
        context = self._build_run_context(pipe_in_plan, proc_run, user, processor, cluster_id)

        # 3. Validate parameters
        errors = processor.validate_parameters(parameters)
        if errors:
            raise ValidationError(errors)

        # 3b. Validate SLURM resources against cluster limits
        slurm_errors = processor.validate_slurm_resources(parameters, cluster_id)
        if slurm_errors:
            raise ValidationError(slurm_errors)

        # 4. Render script
        try:
            script_content = processor.render_script(parameters, context)
        except Exception as e:
            logger.error(f"Error rendering script: {e}", exc_info=True)
            raise ValueError(f"Failed to render script: {e}")

        # 5. Submit to SLURM
        submitter = RemoteJobSubmitter(
            cluster_id=context.cluster_id,
            auth=auth,
            remote_script_dir=processor.get_script_directory(
                scope=context.msi_session.session_plan.scope.name,
                cluster=context.cluster_id,
            ),
        )

        try:
            submitter.connect()

            # Upload and submit script
            output, error = submitter.run_script(
                template_path=None,  # We already have rendered content
                job_name=context.job_name,  # Use job_name from RunContext
                script_content=script_content,  # Pass pre-rendered content
            )

            # Log stderr if present
            if error:
                logger.warning(f"SLURM stderr: {error}")

            # Parse job ID from SLURM output
            job_id = self._parse_job_id(output)
            if not job_id:
                error_msg = f"Could not parse job ID from SLURM output.\nStdout: {output}\nStderr: {error}"
                raise ValueError(error_msg)

            logger.info(f"Submitted job {job_id} for pipe {pipe_in_plan.pipe.name}")

        except Exception as e:
            logger.error(f"Error submitting job: {e}", exc_info=True)
            raise
        finally:
            submitter.close()

        # 6. Create execution records with het-group metadata if applicable
        # Add heterogeneous job info + cluster_id to parameters
        hetjob_info = processor.get_hetjob_info()
        parameters_with_metadata = parameters.copy()
        parameters_with_metadata["cluster_id"] = context.cluster_id or get_default_cluster_id()
        if hetjob_info:
            parameters_with_metadata["_hetjob_info"] = hetjob_info

        pipe_exec = self._create_execution_record(
            pipe_in_plan,
            proc_run,
            user,
            job_id,
            parameters_with_metadata,
            submitter.last_script_path if hasattr(submitter, "last_script_path") else None,
            context.job_name,  # Pass the full job name from context
            script_content,  # Pass the rendered script content for storage
        )

        # 7. Start Django-Q monitoring for status updates
        try:
            from processes.tasks import schedule_pipe_execution_monitoring

            schedule_pipe_execution_monitoring(pipe_exec.id, job_id)
            logger.info(f"Started Django-Q monitoring for PipeExecution {pipe_exec.id}")
        except Exception as e:
            logger.warning(f"Error starting status monitoring: {e}", exc_info=True)

        # 7b. Start universal job status syncer (uses sacct for accurate timing)
        try:
            from processes.tasks import start_job_status_syncer

            cluster_id = parameters_with_metadata["cluster_id"]
            start_job_status_syncer(job_id=job_id, cluster_id=cluster_id)
            logger.info(f"Started job status syncer for job {job_id} on {cluster_id}")
        except Exception as e:
            logger.warning(f"Error starting job status syncer: {e}", exc_info=True)

        # 8. Call processor hooks (may start output syncers)
        try:
            processor.on_job_submit(context, job_id)
        except Exception as e:
            logger.warning(f"Error in on_job_submit hook: {e}", exc_info=True)

        return {
            "job_id": job_id,
            "script_path": submitter.last_script_path if hasattr(submitter, "last_script_path") else None,
            "status": "submitted",
            "pipe_execution_id": pipe_exec.id,
        }

    def _build_run_context(
        self,
        pipe_in_plan: PipeInPlan,
        proc_run: ProcRun,
        user: User,
        processor: BaseProcessor,
        cluster_id: Optional[str] = None,
    ) -> RunContext:
        """
        Build execution context with input data from PipeJoints.

        Args:
            pipe_in_plan: The pipe to execute
            proc_run: The run it belongs to
            user: Executing user
            processor: The processor instance
            cluster_id: Optional cluster ID override

        Returns:
            RunContext with all required information

        Raises:
            ValueError: If required inputs are missing
        """
        # Get PipeJoints that point to this pipe (defines what inputs it needs)
        joints = PipeJoint.objects.filter(pipe_in_plan=pipe_in_plan)

        inputs = {}
        missing_inputs = []

        for joint in joints:
            # Find RunPipeData from the input pipe
            # This is the output of a previous step that we need as input
            input_data = RunPipeData.objects.filter(
                run=proc_run,
                pipe=joint.input_pipe_in_plan.pipe,
                pathtype=joint.input_pathtype,
            ).first()

            if input_data:
                data_type = joint.input_pathtype.data_kind.data_type
                inputs[data_type] = input_data.path.overlay_path
                logger.debug(
                    f"Found input {data_type} from pipe {joint.input_pipe_in_plan.pipe.name}: "
                    f"{input_data.path.overlay_path}",
                )
            else:
                missing_inputs.append(
                    f"{joint.input_pathtype.data_kind.data_type} from {joint.input_pipe_in_plan.pipe.name}",
                )

        if missing_inputs:
            raise ValueError(
                f"Missing required inputs for pipe {pipe_in_plan.pipe.name}: "
                f"{', '.join(missing_inputs)}. "
                f"Make sure dependent pipes have completed successfully.",
            )

        # Get cluster from parameter or software default
        software = pipe_in_plan.pipe.software
        if not cluster_id:
            # Use software's default_cluster, fallback to 'czii' if not set
            cluster_id = getattr(software, "default_cluster", None) or getattr(software, "cluster", "czii")

        # Generate job name for SLURM submission
        # Format: {processor_name}_{session_name}_{run_name}_{pipe_name}
        job_name = f"{processor.name}_{proc_run.msi_session.name}_{proc_run.name}_{pipe_in_plan.name}"

        return RunContext(
            proc_run=proc_run,
            pipe_in_plan=pipe_in_plan,
            msi_session=proc_run.msi_session,
            user=user,
            cluster_id=cluster_id,
            run_number=proc_run.name,
            job_name=job_name,
            inputs=inputs,
        )

    def _parse_job_id(self, slurm_output: str) -> Optional[str]:
        """
        Parse SLURM job ID from sbatch output.

        Args:
            slurm_output: Output from sbatch command

        Returns:
            Job ID string or None if not found

        Example:
            >>> _parse_job_id("Submitted batch job 123456")
            '123456'
        """
        match = re.search(r"Submitted batch job (\d+)", slurm_output)
        if match:
            return match.group(1)
        return None

    def _create_execution_record(
        self,
        pipe_in_plan: PipeInPlan,
        proc_run: ProcRun,
        user: User,
        job_id: str,
        parameters: Dict[str, Any],
        script_path: Optional[str],
        job_name: str,
        script_content: Optional[str] = None,
    ) -> "PipeExecution":
        """
        Create PipeExecution record in database and corresponding JobLog for user tracking.

        Args:
            pipe_in_plan: Pipe that was executed
            proc_run: Run it belongs to
            user: User who submitted the job
            job_id: SLURM job ID
            parameters: Parameters used
            script_path: Path to uploaded script
            job_name: Full descriptive job name from RunContext
            script_content: Full rendered SLURM script content

        Returns:
            Created PipeExecution instance
        """
        from processes.models import PipeExecution

        pipe_exec = PipeExecution.objects.create(
            proc_run=proc_run,
            pipe_in_plan=pipe_in_plan,
            status="submitted",
            job_id=job_id,
            parameters=parameters,
            script_path=script_path,
            script_content=script_content,
            submitted_at=timezone.now(),
        )

        logger.info(f"Created PipeExecution record {pipe_exec.id} for job {job_id}")

        # Create JobLog record for user tracking
        try:
            # Use the full job name from RunContext (e.g., "aretomo3_24nov10_run001_vol001")
            job_log = JobLog.objects.create(
                user=user,
                job_id=job_id,
                job_name=job_name,
                parameters=parameters,
                advanced=False,  # Workflow-launched jobs are not "advanced" manual submissions
            )
            logger.info(f"Created JobLog record {job_log.id} for job {job_id} ({job_name}) by user {user.username}")
        except Exception as e:
            # Don't fail the whole submission if JobLog creation fails
            logger.warning(f"Failed to create JobLog for job {job_id}: {e}", exc_info=True)

        return pipe_exec

    def check_dependencies_met(
        self,
        proc_run: ProcRun,
        pipe_in_plan: PipeInPlan,
    ) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies for a pipe are met.

        A dependency is met if:
        - The pipe has a PipeJoint defining the input
        - The input pipe has completed execution
        - The output file exists in RunPipeData

        Args:
            proc_run: The run
            pipe_in_plan: The pipe to check

        Returns:
            Tuple of (dependencies_met: bool, missing: List[str])

        Example:
            met, missing = executor.check_dependencies_met(run, pipe)
            if not met:
                print(f"Cannot execute: missing {', '.join(missing)}")
        """
        from processes.models import PipeExecution

        joints = PipeJoint.objects.filter(pipe_in_plan=pipe_in_plan)

        if not joints.exists():
            # No dependencies
            return True, []

        missing = []

        for joint in joints:
            # Check if input pipe has completed
            input_execution = PipeExecution.objects.filter(
                proc_run=proc_run,
                pipe_in_plan=joint.input_pipe_in_plan,
                status="completed",
            ).first()

            if not input_execution:
                missing.append(
                    f"{joint.input_pathtype.data_kind.data_type} "
                    f"from {joint.input_pipe_in_plan.pipe.name} (not completed)",
                )
                continue

            # Check if output exists in RunPipeData
            output_exists = RunPipeData.objects.filter(
                run=proc_run,
                pipe=joint.input_pipe_in_plan.pipe,
                pathtype=joint.input_pathtype,
            ).exists()

            if not output_exists:
                missing.append(
                    f"{joint.input_pathtype.data_kind.data_type} "
                    f"from {joint.input_pipe_in_plan.pipe.name} (no output data)",
                )

        return len(missing) == 0, missing
