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
                'workflow': 'aretomo3',
                'pipe': 'vol10a',
                'scope': 'krios1',
                'cluster': 'czii'
            }

        See `stores.placeholders` for what each token means in this lane -- notably
        {proc_run} is the processing run and {run} is a per-file tilt-series id, which is
        the opposite of how review templates read them.
        """
        proc_software = self.pipe_in_plan.pipe.software.name
        return {
            "proc_plan": self.proc_run.proc_plan.name,
            "proc_run": self.proc_run.name,
            "msi_session": self.msi_session.name,
            "proc_software": proc_software,
            # Legacy alias for {proc_software}; see PipeInPlan.get_replacement_map.
            "workflow": proc_software,
            "pipe": self.pipe_in_plan.pipe.name,
            "scope": self.msi_session.session_plan.scope.name,
            "cluster": self.cluster_id,
        }
