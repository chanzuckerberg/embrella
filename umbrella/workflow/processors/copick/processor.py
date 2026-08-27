"""
Copick processor for the generic pipeline execution system.

This processor handles Copick project creation, tomogram import, and downsampling.
Copick is a framework for managing cryo-ET data and annotations.
"""

import logging
import os
import re
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from workflow.context import RunContext
from workflow.processors import get_processor, register_processor
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class CopickProcessor(BaseProcessor):
    """
    Copick processor for managing cryo-ET data projects.

    This processor creates Copick projects, imports tomograms from
    AreTomo3 or DenoisET outputs, and performs downsampling.
    """

    name = "copick"
    display_name = "Copick"
    version = "1.0.1"
    cluster = "bruno"
    allowed_clusters = ["bruno", "czii"]
    task_name = "copick_project"

    # Schema is now loaded from schema.yaml file

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate Copick parameters based on operation mode.

        Args:
            params: Parameter dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate operation is valid
        operation = params.get("operation", "create")
        if operation not in ["create", "add_object", "import_tomograms"]:
            errors.append("operation must be 'create', 'add_object', or 'import_tomograms'")
            return errors  # Can't validate further without valid operation

        # Validate create mode parameters
        if operation == "create":
            if not params.get("import_tomo_type"):
                errors.append("import_tomo_type is required for create operation")
            if not params.get("import_tomogram_run"):
                errors.append("import_tomogram_run is required for create operation")

        # Validate import_tomograms mode parameters
        if operation == "import_tomograms":
            if not params.get("copick_session"):
                errors.append("copick_session is required for import_tomograms operation")
            if not params.get("copick_run"):
                errors.append("copick_run is required for import_tomograms operation")
            if not params.get("import_tomo_type"):
                errors.append("import_tomo_type is required for import_tomograms operation")
            if not params.get("import_tomogram_run"):
                errors.append("import_tomogram_run is required for import_tomograms operation")

        # Validate add_object mode parameters
        if operation == "add_object":
            required_fields = ["copick_session", "copick_run", "object_name", "object_diameter"]
            for field in required_fields:
                if not params.get(field):
                    errors.append(f"{field} is required for add_object operation")

            # Validate that either template_map_name or object_map_file is provided
            if not params.get("template_map_name") and not params.get("object_map_file"):
                errors.append("Either template_map_name or object_map_file must be provided for add_object operation")

            # If object_map_file is provided, object_voxel_size is required
            if params.get("object_map_file") and not params.get("object_voxel_size"):
                errors.append("object_voxel_size is required when object_map_file is provided")

            # Validate PDB ID format if provided
            pdb_id = params.get("pdb_id")
            if pdb_id:
                if not re.match(r"^[0-9][A-Za-z0-9]{3}$", pdb_id):
                    errors.append("pdb_id must be 4 characters (starting with a digit)")

        return errors

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        """
        Render the Copick SLURM job script based on operation mode.

        Args:
            params: Validated parameters
            run_context: Execution context with session, run, and user info

        Returns:
            Rendered bash script for SLURM submission
        """
        # Get template from processor's templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))

        # Select template based on operation
        operation = params.get("operation", "create")
        template_map = {
            "create": "copick_tomograms.sh.j2",
            "add_object": "add_object.sh.j2",
            "import_tomograms": "copick_tomograms.sh.j2",  # Same template as create
        }
        template_file = template_map.get(operation, "copick_tomograms.sh.j2")
        template = env.get_template(template_file)

        # Get session and run information based on operation
        # For add_object and import_tomograms, use copick_session from params
        # For create, use MSI session from run_context
        if operation in ["add_object", "import_tomograms"]:
            session_name = params.get("copick_session")
        else:
            session_name = run_context.msi_session.name
        copick_run = run_context.run_number

        # Get structured template context (includes SLURM directives)
        context = self.get_template_context(params, run_context)

        # Lazy: workflow.syncers pulls in workflow.views at import time.
        from workflow.syncers import rec_file_pattern

        # Build template variables based on operation
        template_vars = {
            "operation": operation,  # Pass operation to template for conditionals
            "session": session_name,
            "copickRun": copick_run,
            "copick_root": self.get_processing_base_path(cluster=run_context.cluster_id),
            # The one Position-naming contract, from the same row the syncers parse with.
            # copick's --run-regex matches run *stems*, so the basename regex drops .zarr.
            "run_regex": rec_file_pattern().regex.replace(r"\.zarr$", "$"),
            "slurm_directives": context.get("slurm_directives", []),
            "context_vars": context.get("context_vars", {}),
        }

        # Tomogram imports read across software: the source trees resolve through the
        # owning processor so per-software overrides keep applying.
        if operation in ("create", "import_tomograms"):
            for var, source in (("aretomo3_root", "aretomo3"), ("denoise_root", "denoiset")):
                template_vars[var] = get_processor(source).get_processing_base_path(cluster=run_context.cluster_id)

        # Add operation-specific variables
        if operation == "create":
            template_vars.update(
                {
                    "importTomoType": params["import_tomo_type"],
                    "importTomogramRun": params["import_tomogram_run"],
                    "downsampleTomogramVoxelSize": params.get("downsample_voxel_size", ""),
                }
            )
        elif operation == "import_tomograms":
            template_vars.update(
                {
                    "copickRunName": params["copick_run"],  # Existing copick run to import into
                    "importTomoType": params["import_tomo_type"],
                    "importTomogramRun": params["import_tomogram_run"],
                    "downsampleTomogramVoxelSize": params.get("downsample_voxel_size", ""),
                }
            )
        elif operation == "add_object":
            template_vars.update(
                {
                    "copickSession": params["copick_session"],
                    "copickRunName": params["copick_run"],
                    "objectName": params["object_name"],
                    "objectDiameter": params["object_diameter"],
                    "templateMapName": params.get("template_map_name", ""),
                    "pdbId": params.get("pdb_id", ""),
                    "objectMapFile": params.get("object_map_file", ""),
                    "objectVoxelSize": params.get("object_voxel_size", ""),
                }
            )

        # Render template with parameters
        script = template.render(**template_vars)

        logger.info(
            f"Rendered Copick {operation} script for session {session_name}, copick_run {copick_run}",
        )

        return script

    def parse_output_paths(self, run_context: RunContext) -> List[Dict[str, Any]]:
        """
        Define expected output paths for Copick.

        Args:
            run_context: Execution context

        Returns:
            List of output path specifications
        """
        session_name = run_context.msi_session.name
        copick_run = run_context.run_number

        base_path = f"/hpc/projects/group.czii/krios1.processing/copick/{session_name}/{copick_run}"

        return [
            {
                "type": "config",
                "pattern": f"{base_path}/config.json",
                "description": "Copick project configuration file",
            },
            {
                "type": "runs",
                "pattern": f"{base_path}/ExperimentRuns/*",
                "description": "Copick experiment runs",
            },
            {
                "type": "picks",
                "pattern": f"{base_path}/*/picks/*.zarr",
                "description": "Particle picks in Zarr format",
            },
            {
                "type": "meshes",
                "pattern": f"{base_path}/*/meshes/*.glb",
                "description": "Mesh annotations",
            },
            {
                "type": "logs",
                "pattern": f"{base_path}/*.log",
                "description": "Processing logs",
            },
        ]

    def get_default_slurm_options(self) -> Dict[str, Any]:
        """
        Get default SLURM options for Copick jobs.

        Returns:
            Dictionary of SLURM options
        """
        return {
            "partition": "gpu",
            "gpus": 1,
            "nodes": 1,
            "cpus_per_task": 8,
            "mem_per_cpu": "196G",  # Copick requires large memory for tomogram processing
            "time": "140:00:00",  # ~6 days for large projects
            "job_name": "copick",
        }

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        """
        Hook called after successful job submission.

        Args:
            run_context: Execution context
            job_id: SLURM job ID
        """
        logger.info(
            f"Copick job {job_id} submitted for session {run_context.msi_session.name}, run {run_context.run_number}",
        )

        # Note: Copick creates its own directory structure and logs
        # No additional syncing needed during execution

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        """
        Hook called when job completes.

        Args:
            run_context: Execution context
            success: True if job completed successfully, False if failed
        """
        if success:
            logger.info(
                f"Copick job completed successfully for session {run_context.msi_session.name}, "
                f"run {run_context.run_number}",
            )
        else:
            logger.warning(
                f"Copick job failed for session {run_context.msi_session.name}, run {run_context.run_number}",
            )

    def get_input_dependencies(self) -> List[str]:
        """
        Return list of processor names that must complete before this one.

        NOTE: Copick uses parameter-based input selection (import_tomogram_run parameter)
        rather than PipeJoint-based dependencies, so we return an empty list here.
        The frontend will validate that the selected import_tomogram_run exists.

        Returns:
            List of prerequisite processor names (empty for copick)
        """
        return []  # No PipeJoint dependencies - uses import_tomogram_run parameter instead


# Register the processor after the class is fully defined to avoid circular imports
register_processor(CopickProcessor)
