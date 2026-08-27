"""
DenoisET processor for the generic pipeline execution system.

This processor handles denoising of tomographic reconstructions using DenoisET.
It takes AreTomo3 output volumes as input and produces denoised versions.
"""

import logging
import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from workflow.context import RunContext
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class DenoisETProcessor(BaseProcessor):
    """
    DenoisET processor for denoising tomographic reconstructions.

    This processor applies trained DenoisET models to tomographic volumes
    to reduce noise while preserving structural features.
    """

    name = "denoiset"
    display_name = "DenoisET"
    version = "1.0"
    cluster = "czii"
    allowed_clusters = ["czii", "bruno"]
    task_name = "denoising"

    # Schema is now loaded from schema.yaml file

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate DenoisET parameters.

        Args:
            params: Parameter dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate aretomo_run is provided
        if not params.get("aretomo_run"):
            errors.append("aretomo_run is required and must not be empty")

        # Validate model_name is provided
        if not params.get("model_name"):
            errors.append("model_name is required and must not be empty")

        return errors

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        """
        Render the DenoisET SLURM job script using schema-driven approach.

        Args:
            params: Validated parameters
            run_context: Execution context with session, run, and user info

        Returns:
            Rendered bash script for SLURM submission
        """
        # Get template from processor's templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        template_file = "denoiset.sh.j2"

        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_file)

        # Get session and run information
        session_name = run_context.msi_session.name
        denoise_run = run_context.run_number

        # Get structured template context (schema-driven approach)
        context = self.get_template_context(params, run_context)

        # Add DenoisET-specific context variables
        context["context_vars"]["session"] = session_name
        context["context_vars"]["denoise_run"] = denoise_run

        # For backwards compatibility with old template (temporary):
        # Flatten context into template_vars for the old hardcoded template
        # This will be removed once template is updated to use Jinja loops
        template_vars = {}

        # Add flattened variables at top level for backwards compatibility
        template_vars.update(context["context_vars"])
        template_vars.update(context["calculated_vars"])
        for var_name, var_info in context["schema_vars"].items():
            template_vars[var_name] = var_info["value"]
        template_vars.update(context["control_vars"])

        # Add structured context for new Jinja loop-based template
        template_vars["context_vars"] = context["context_vars"]
        template_vars["calculated_vars"] = context["calculated_vars"]
        template_vars["schema_vars"] = context["schema_vars"]
        template_vars["control_vars"] = context["control_vars"]
        template_vars["cli_args"] = context["cli_args"]
        template_vars["slurm_directives"] = context.get("slurm_directives", [])
        template_vars["cluster"] = run_context.cluster_id

        # Render template with schema-driven variables
        script = template.render(**template_vars)

        logger.info(
            f"Rendered DenoisET script for session {session_name}, "
            f"aretomo_run {params['aretomo_run']}, denoise_run {denoise_run}",
        )

        return script

    def parse_output_paths(self, run_context: RunContext) -> List[Dict[str, Any]]:
        """
        Define expected output paths for DenoisET.

        Args:
            run_context: Execution context

        Returns:
            List of output path specifications
        """
        session_name = run_context.msi_session.name
        denoise_run = run_context.run_number

        root = self.get_processing_base_path(
            scope=run_context.msi_session.session_plan.scope.name,
            cluster=run_context.cluster_id,
        )
        base_path = f"{root}/{session_name}/{denoise_run}"

        return [
            {
                "type": "denoised_volumes",
                "pattern": f"{base_path}/*.mrc",
                "description": "Denoised tomographic volumes",
            },
            {
                "type": "rechunked",
                "pattern": f"{base_path}/rechunked/*.zarr",
                "description": "Rechunked Zarr arrays",
            },
            {
                "type": "plots",
                "pattern": f"{base_path}/plots/*.png",
                "description": "Quality control plots",
            },
            {
                "type": "logs",
                "pattern": f"{base_path}/logs/*.log",
                "description": "Processing logs",
            },
        ]

    def get_default_slurm_options(self) -> Dict[str, Any]:
        """
        Get default SLURM options for DenoisET jobs.

        Returns:
            Dictionary of SLURM options
        """
        return {
            "partition": "gpu",
            "gpus": 1,  # DenoisET uses single GPU
            "nodes": 1,
            "cpus_per_task": 8,
            "mem_per_gpu": "32G",
            "time": "12:00:00",  # 12 hours
            "job_name": "denoiset",
        }

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        """
        Hook called after successful job submission.

        For DenoisET, start a syncer to monitor outputs and create ReviewTomogram records.

        Args:
            run_context: Execution context
            job_id: SLURM job ID
        """
        logger.info(
            f"DenoisET job {job_id} submitted for session {run_context.msi_session.name}, run {run_context.run_number}",
        )

        # Start denoise syncer as Django-Q task to monitor for output files
        # Note: base_path defaults to get_processing_base_path() in BaseProcessor
        self._start_syncer_task(
            syncer_class_path="workflow.processors.denoiset.syncer.DenoiseSyncer",
            run_context=run_context,
            job_id=job_id,
        )

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        """
        Hook called when job completes.

        Args:
            run_context: Execution context
            success: True if job completed successfully, False if failed
        """
        if success:
            logger.info(
                f"DenoisET job completed successfully for session {run_context.msi_session.name}, "
                f"run {run_context.run_number}",
            )
        else:
            logger.warning(
                f"DenoisET job failed for session {run_context.msi_session.name}, run {run_context.run_number}",
            )

    def get_input_dependencies(self) -> List[str]:
        """
        Return list of processor names that must complete before this one.

        NOTE: DenoisET uses parameter-based input selection (aretomo_run parameter)
        rather than PipeJoint-based dependencies, so we return an empty list here.
        The frontend will validate that the selected aretomo_run exists via the
        dynamic dropdown.

        Returns:
            List of prerequisite processor names (empty for denoiset)
        """
        return []  # No PipeJoint dependencies - uses aretomo_run parameter instead


# Register the processor after the class is fully defined to avoid circular imports
from workflow.processors import register_processor

register_processor(DenoisETProcessor)
