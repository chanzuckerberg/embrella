"""
Membrane Segmentation processor for the generic pipeline execution system.

This processor runs membrain-seg inference on Copick tomograms to generate
membrane segmentations using the copick inference membrain-seg command.
"""

import logging
import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from workflow.context import RunContext
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class MembranesegProcessor(BaseProcessor):
    """
    Membrane Segmentation processor for Copick tomograms.

    This processor takes output from Copick projects and runs membrain-seg
    inference to generate membrane segmentations.
    """

    name = "membraneseg"
    display_name = "Membrane Segmentation"
    version = "1.0"
    cluster = "bruno"
    allowed_clusters = ["bruno", "czii"]
    task_name = "membrane_segmentation"

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate membrane segmentation parameters.

        Args:
            params: Parameter dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Required fields
        required_fields = ["copick_session", "copick_procrun", "tomo_type", "tomo_voxel_size"]
        for field in required_fields:
            if not params.get(field):
                errors.append(f"{field} is required")

        # Validate voxel size if provided
        tomo_voxel_size = params.get("tomo_voxel_size")
        if tomo_voxel_size is not None:
            try:
                voxel_size = float(tomo_voxel_size)
                if voxel_size < 1.0 or voxel_size > 100.0:
                    errors.append("tomo_voxel_size must be between 1.0 and 100.0 Angstroms")
            except (ValueError, TypeError):
                errors.append("tomo_voxel_size must be a valid number")

        # Validate threshold if provided (must be numeric)
        threshold = params.get("threshold")
        if threshold is not None and threshold != "":
            try:
                float(threshold)
            except (ValueError, TypeError):
                errors.append("threshold must be a valid number if provided")

        return errors

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        """
        Render the membrane segmentation SLURM job script.

        Args:
            params: Validated parameters
            run_context: Execution context with session, run, and user info

        Returns:
            Rendered bash script for SLURM submission
        """
        # Get template from processor's templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("membraneseg.sh.j2")

        # Get structured template context (includes SLURM directives)
        context = self.get_template_context(params, run_context)

        # Build template variables
        # Use copick_session from params (not MSI session)
        session_name = params.get("copick_session")
        copick_procrun = params.get("copick_procrun")

        # Generate a unique session ID for this membraneseg run
        membraneseg_session_id = run_context.run_number

        # The project tree belongs to copick; its root resolves through that processor.
        from workflow.processors import get_processor

        copick_root = get_processor("copick").get_processing_base_path(cluster=run_context.cluster_id)

        template_vars = {
            "job_name": f"{session_name}_membraneseg_{copick_procrun}_{membraneseg_session_id}",
            "session": session_name,
            "copick_root": copick_root,
            "copick_procrun": copick_procrun,
            "tomo_type": params["tomo_type"],
            "tomo_voxel_size": params["tomo_voxel_size"],
            "membraneseg_session_id": membraneseg_session_id,
            "threshold": params.get("threshold", ""),
            "slurm_directives": context.get("slurm_directives", []),
            "context_vars": context.get("context_vars", {}),
        }

        # Render template with parameters
        script = template.render(**template_vars)

        logger.info(
            f"Rendered membraneseg script for session {session_name}, "
            f"copick_procrun {copick_procrun}, tomo_type {params['tomo_type']}",
        )

        return script

    def get_default_slurm_options(self) -> Dict[str, Any]:
        """
        Get default SLURM options for membrane segmentation jobs.

        Returns:
            Dictionary of SLURM options
        """
        return {
            "partition": "gpu",
            "gpus": 4,
            "nodes": 1,
            "cpus_per_task": 4,
            "mem_per_cpu": "32G",
            "time": "72:00:00",
            "job_name": "membraneseg",
        }

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        """
        Hook called after successful job submission.

        Args:
            run_context: Execution context
            job_id: SLURM job ID
        """
        logger.info(
            f"Membrane segmentation job {job_id} submitted for run {run_context.run_number}",
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
                f"Membrane segmentation job completed successfully for run {run_context.run_number}",
            )
        else:
            logger.warning(
                f"Membrane segmentation job failed for run {run_context.run_number}",
            )

    def get_input_dependencies(self) -> List[str]:
        """
        Return list of processor names that must complete before this one.

        Membrane segmentation requires Copick to have imported tomograms first.

        Returns:
            List of prerequisite processor names
        """
        return ["copick"]


# Register the processor after the class is fully defined to avoid circular imports
from workflow.processors import register_processor

register_processor(MembranesegProcessor)
