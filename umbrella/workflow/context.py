"""
Shared context and types for workflow execution.

This module contains shared data structures used by both the execution
system and processors to avoid circular imports.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from django.contrib.auth.models import User
from processes.models import PipeInPlan, ProcRun
from tem.models import MsiSession


@dataclass
class RunContext:
    """
    Context object passed to processors during execution.

    Contains all information needed to execute a pipeline step:
    - Database references (run, pipe, session, user)
    - Cluster information
    - Input data from previous steps
    - Job name for SLURM submission

    Example usage:
        context = RunContext(
            proc_run=proc_run,
            pipe_in_plan=pipe_in_plan,
            msi_session=session,
            user=request.user,
            cluster_id='czii',
            run_number='run_001',
            job_name='aretomo3_24nov10_run001_vol10a',
            inputs={'mrc_stack': '/path/to/stack.mrc'}
        )

        # Processors access inputs like:
        stack_path = context.get_input('mrc_stack', required=True)
    """

    proc_run: ProcRun
    pipe_in_plan: PipeInPlan
    msi_session: MsiSession
    user: User
    cluster_id: str
    run_number: str
    job_name: str
    inputs: Dict[str, str]  # Maps data_type to file path

    def get_input(self, data_type: str, required: bool = False) -> Optional[str]:
        """
        Get an input path by data type.

        Args:
            data_type: The type of data to retrieve (e.g., 'mrc_stack', 'ctf')
            required: If True, raises ValueError if input not found

        Returns:
            Path to the input file, or None if not found and not required

        Raises:
            ValueError: If required=True and input not found

        Example:
            stack = context.get_input('mrc_stack', required=True)
            ctf = context.get_input('ctf')  # Returns None if not present
        """
        if data_type in self.inputs:
            return self.inputs[data_type]

        if required:
            available = ", ".join(sorted(self.inputs.keys()))
            raise ValueError(
                f"Required input '{data_type}' not found. Available inputs: {available if available else 'none'}",
            )

        return None

    def get_output_base_path(self) -> str:
        """
        Get base output directory for this pipeline step.

        Returns:
            Absolute path on cluster: /hpc/projects/group.czii/{cluster}.processing/{software}/{session}/{run}/

        Example:
            /hpc/projects/group.czii/czii.processing/aretomo3/24nov10/run001/
        """
        from stores.models import fill_place_holders

        template = "/hpc/projects/group.czii/{cluster}.processing/{proc_software}/{msi_session}/{proc_run}/"
        return fill_place_holders(template, self.get_placeholder_map())

    def get_placeholder_map(self) -> Dict[str, str]:
        """
        Get placeholder map for path generation.

        Returns:
            Dict mapping placeholder names to values:
            {
                'proc_plan': 'czii-live',
                'proc_run': 'run001',
                'msi_session': '24nov10',
                'proc_software': 'aretomo3',
                'pipe': 'vol10a',
                'scope': 'Krios1',
                'cluster': 'czii'
            }
        """
        return {
            "proc_plan": self.proc_run.proc_plan.name,
            "proc_run": self.proc_run.name,
            "msi_session": self.msi_session.name,
            "proc_software": self.pipe_in_plan.pipe.software.name,
            "pipe": self.pipe_in_plan.pipe.name,
            "scope": self.msi_session.session_plan.scope.name,
            "cluster": self.cluster_id,
        }

    def format_paths(self, template: str) -> str:
        """
        Fill placeholders in a path template using run context.

        Supports placeholders like {session}, {run}, {user}, etc.

        Args:
            template: Path template with {placeholders}

        Returns:
            Formatted path with placeholders replaced

        Example:
            path = context.format_paths('/data/{session}/{run}/output.mrc')
            # Returns: '/data/20240315_Session1/run_001/output.mrc'
        """
        from stores.models import fill_place_holders

        return fill_place_holders(
            template,
            session=self.msi_session,
            run=self.proc_run,
            user=self.user,
        )
