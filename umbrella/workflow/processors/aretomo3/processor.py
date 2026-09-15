"""
AreTomo3 Processor

Handles execution of AreTomo3 tomographic reconstruction jobs.
Supports both basic and advanced parameter configurations.
"""

import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from tem.models import GAIN_ROLE
from umbrella_logger import logger

from workflow.context import RunContext
from workflow.processors.aretomo3.gain_file_fetcher import list_gain_files
from workflow.processors.base import BaseProcessor

# What MsiSession.get_session_dir returns when the plan emits no such role
NO_DIRECTORY = "."

# GatanCeltic gain format; AreTomo3 cannot read it, the script converts it to .mrc first
DM4_SUFFIX = ".dm4"

# Super-resolution frames have half the sensor pixel. Read off the session, not the form,
# so the key is injected into params at render time and is never a schema property.
SUPER_RES_KEY = "super_resolution"
SUPER_RES_FACTOR = 2

# Auto -AtBin targets, in Angstroms per voxel
TARGET_5A = 5
TARGET_10A = 10

# Import register_processor here to avoid circular import
# (it will be called at module import time but after the class is defined)


class AreTomo3Processor(BaseProcessor):
    """Processor for AreTomo3 tomographic reconstruction."""

    name = "aretomo3"
    display_name = "AreTomo3"
    version = "2.3.0"
    cluster = "czii"
    allowed_clusters = ["czii", "bruno"]
    task_name = "tomographic_reconstruction"

    def _schema_default(self, key: str) -> Any:
        return self.get_parameter_schema()["properties"][key].get("default")

    def _param(self, params: Dict[str, Any], key: str) -> Any:
        """The posted value, else the schema default: bare params (validation) lack merged defaults."""
        value = params.get(key)
        return self._schema_default(key) if value in (None, "") else value

    def _frame_pixel_size(self, params: Dict[str, Any]) -> float:
        """What -PixSize gets: the sensor pixel, halved for super-resolution frames."""
        pixel_size = float(params["pixel_size"])
        if params.get(SUPER_RES_KEY):
            return pixel_size / SUPER_RES_FACTOR
        return pixel_size

    def _calculate_auto_binning(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        -AtBin factors that land the tomograms at 5Å and 10Å.

        -AtBin is relative to the motion-corrected series, whose pixel is:

            sensor_px ──(÷2 if super_res)──▶ frame_px ──(× McBin ÷ EerSampling)──▶ mc_px

        EerSampling only upsamples EER frames; an admin ParameterDefaults row sets it to 1
        for TIFF cameras.

        Example:
            pixel_size=1.54, mc_bin=2, eer_sampling=2 → {"tomo_bin_5A": 3.25, "tomo_bin_10A": 6.49}
        """
        mc_pixel = self._frame_pixel_size(params) * float(self._param(params, "mc_bin"))
        mc_pixel /= float(self._param(params, "eer_sampling"))
        return {
            "tomo_bin_5A": round(TARGET_5A / mc_pixel, 3),
            "tomo_bin_10A": round(TARGET_10A / mc_pixel, 3),
        }

    def _apply_acquisition(self, params: Dict[str, Any], run_context: "RunContext") -> Dict[str, Any]:
        """Copy of params carrying the session's acquisition facts the formatters need."""
        return {**params, SUPER_RES_KEY: run_context.msi_session.super_resolution}

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate AreTomo3 parameters beyond JSON Schema.

        Args:
            params: User-provided parameters

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate advanced parameters if enabled
        if params.get("use_advanced_params"):
            advanced_params = ["tilt_axis", "vol_z", "align_z"]
            missing = [p for p in advanced_params if p not in params]
            if missing:
                errors.append(
                    f"Advanced parameters required when use_advanced_params is true: {', '.join(missing)}",
                )

        # Validate pixel size for binning calculation
        pixel_size = params.get("pixel_size")
        if pixel_size:
            try:
                binning = self._calculate_auto_binning(params)
                if binning["tomo_bin_5A"] < 1 or binning["tomo_bin_10A"] < 1:
                    errors.append("Pixel size results in invalid binning factors (< 1)")
            except (ValueError, ZeroDivisionError):
                errors.append("Invalid pixel_size value for binning calculation")

        # Validate multi-value string format parameters
        multi_value_params = {
            "mc_patch": 2,
            "group_frames": 2,
            "mag_correction": 3,
            "ext_phase": 2,
            "recon_range": 2,
            "sart_iterations": 2,
            "at_bin": (0, 1, 2, 3),  # 0-3 input values allowed
        }

        for param_name, expected_count in multi_value_params.items():
            value = params.get(param_name)
            if value and str(value).strip():
                parts = str(value).strip().split()

                if isinstance(expected_count, int):
                    if len(parts) != expected_count:
                        errors.append(
                            f"{param_name} must have exactly {expected_count} space-separated values, got {len(parts)}",
                        )
                elif isinstance(expected_count, tuple):
                    if len(parts) not in expected_count:
                        expected_str = " or ".join(map(str, expected_count))
                        errors.append(
                            f"{param_name} must have {expected_str} space-separated values, got {len(parts)}",
                        )

        # Validate mode interaction (Cmd and Resume)
        cmd_mode = params.get("cmd_mode", 0)
        resume = params.get("resume_processing", False)
        if cmd_mode in [1, 2] and resume:
            errors.append(
                "resume_processing is ignored when cmd_mode is 1 or 2 (per AreTomo3 documentation: -Cmd 1 and -Cmd 2 ignore -Resume)",
            )

        return errors

    # Custom formatters for schema-driven CLI generation
    def _format_cli_tilt_axis_with_refine(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Format tilt_axis parameter with refinement flag.

        Combines tilt_axis and tilt_axis_refine into single CLI argument.
        Example: tilt_axis=85, tilt_axis_refine=1 → "85 1"
        """
        tilt_axis = value if value is not None else 0
        tilt_axis_refine = params.get("tilt_axis_refine", 1)
        return f"{tilt_axis} {tilt_axis_refine}"

    def _format_cli_boolean_to_int(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Convert boolean value to integer string for CLI.

        Used for parameters like tilt_offset and denoise_training.
        Example: True → "1", False → "0"
        """
        if value:
            return "1"
        return "0"

    def _format_cli_local_shift_values(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Format local_shift parameter to CLI values.

        Converts local_shift value to patch size parameters.
        Example: value > 0 → "4 4", value == 0 or None → "0 0"
        """
        if value and value > 0:
            return "4 4"
        return "0 0"

    def _format_cli_thickness_to_temp_dir(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Format thickness_measure parameter to temp directory path.

        Converts thickness measurement boolean/int to temp directory or "0".
        Example: 1 → "/tmp/aretomo3_thickness", 0 → "0"
        """
        if value and value != 0:
            return "/tmp/aretomo3_thickness"
        return "0"

    def _format_cli_path_resolver(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Absolute path passthrough for defect files, dark references, etc.

        Args:
            value: Absolute path on the cluster
            params: All parameters

        Returns:
            The trimmed path, or empty string if value is empty
        """
        if not value:
            return ""
        return str(value).strip()

    def _format_cli_pix_size_frame(self, value: Any, params: Dict[str, Any]) -> str:
        """-PixSize is the frame pixel, not the sensor pixel the form holds. See _frame_pixel_size."""
        return str(self._frame_pixel_size(params))

    def _format_cli_at_bin_auto(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Format -AtBin parameter with auto-calculation when empty.

        If at_bin has a user-provided value, use it directly.
        If at_bin is empty, auto-calculate from the motion-corrected pixel (see
        _calculate_auto_binning): 5Å, 10Å, 10Å.

        Args:
            value: User-provided at_bin value (may be empty string)
            params: All parameters (must include pixel_size)

        Returns:
            Formatted string with 1 or 3 binning factors

        Example:
            value="" with pixel_size=1.54, mc_bin=2, eer_sampling=2 → "3.25 6.49 6.49"
            value="2.0" → "2.0"
            value="1.5 3.0 3.0" → "1.5 3.0 3.0"
        """
        # If user provided a value, use it directly
        if value and str(value).strip():
            return str(value).strip()

        # Auto-calculate based on pixel_size
        pixel_size = params.get("pixel_size")
        if not pixel_size:
            # No pixel_size available, return empty (will be skipped)
            return ""

        try:
            binning = self._calculate_auto_binning(params)
            return f"{binning['tomo_bin_5A']} {binning['tomo_bin_10A']} {binning['tomo_bin_10A']}"
        except (ValueError, ZeroDivisionError):
            return ""

    def _handle_multi_var_local_shift(self, value: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle local_shift parameter mapping to multiple bash variables.

        Maps single local_shift parameter to local_aln_1 and local_aln_2.
        Example: value > 0 → {"local_aln_1": 4, "local_aln_2": 4}
                 value == 0 → {"local_aln_1": 0, "local_aln_2": 0}
        """
        if value and value > 0:
            return {
                "local_aln_1": 4,
                "local_aln_2": 4,
            }
        return {
            "local_aln_1": 0,
            "local_aln_2": 0,
        }

    def get_calculated_vars(
        self,
        params: Dict[str, Any],
        run_context: "RunContext",
    ) -> Dict[str, Any]:
        """
        Get AreTomo3-specific calculated variables.

        Calculates binning factors based on pixel size and extracts
        compute resource parameters for use in the template.

        Args:
            params: Validated parameters
            run_context: Execution context

        Returns:
            Dict with calculated variables for template
        """
        binning = self._calculate_auto_binning(params)
        return {
            "sensor_pix_size": float(params["pixel_size"]),
            "frame_pix_size": self._frame_pixel_size(params),
            "tomo_bin_5A": binning["tomo_bin_5A"],
            "tomo_bin_10A": binning["tomo_bin_10A"],
            "slurm_component_0_gpus": int(params.get("slurm_component_0_gpus", 8)),
        }

    def _resolve_gain_file_path(self, params: Dict[str, Any], run_context: "RunContext") -> Dict[str, Any]:
        """
        Resolve gain file path for the template.

        An absolute gain_file_name is used as-is. Otherwise the session's gain
        directory is resolved (plan binding, else the camera's template); an empty
        name picks the newest file listed there.

        Args:
            params: User-provided parameters
            run_context: Execution context with session and cluster

        Returns:
            Updated params dict with gain_file_path (full path to gain file)
        """
        params = params.copy()  # Don't mutate original

        gain_file_name = params.get("gain_file_name", "").strip()
        if os.path.isabs(gain_file_name):
            params["gain_file_path"] = gain_file_name
            return params

        session = run_context.msi_session
        directory = session.get_session_dir(GAIN_ROLE)
        if directory == NO_DIRECTORY:
            raise ValueError(
                f"Session {session.name} resolves no gain directory; set gain on its camera, "
                f"bind role '{GAIN_ROLE}' on its plan, or give an absolute path."
            )

        if not gain_file_name:
            logger.info(f"No gain file specified, fetching most recent from {directory}")
            pattern = session.get_file_pattern(GAIN_ROLE)
            result = list_gain_files(directory, cluster_id=run_context.cluster_id, file_pattern=pattern)
            if not (result["success"] and result["files"]):
                error_msg = result.get("error") or "no files matched"
                logger.error(f"Failed to fetch gain files from cluster: {error_msg}")
                raise ValueError(f"No gain file specified and failed to fetch from cluster: {error_msg}")
            gain_file_name = result["files"][0]["filename"]
            logger.info(f"Resolved gain file to most recent: {gain_file_name}")

        gain_file_path = os.path.join(directory, gain_file_name)
        params["gain_file_path"] = gain_file_path
        logger.info(f"Gain file path: {gain_file_path}")

        return params

    def _mdoc_dir(self, session) -> str:
        """The session's mdoc directory; AreTomo3 cannot run without one."""
        mdoc_dir = session.get_session_dir("mdocs")
        if mdoc_dir == NO_DIRECTORY:
            raise ValueError(f"Session {session.name} resolves no mdocs directory; bind one on its plan.")
        return mdoc_dir.rstrip("/")

    def render_script(self, params: Dict[str, Any], run_context: "RunContext") -> str:
        """
        Render AreTomo3 job script using Jinja2 template with schema-driven generation.

        Args:
            params: Validated parameters
            run_context: Execution context with session, run, inputs

        Returns:
            Rendered bash script as string
        """
        # Resolve gain file path (fetches most recent if not specified, builds full path)
        params = self._resolve_gain_file_path(params, run_context)
        params = self._apply_acquisition(params, run_context)

        # Get template from processor's templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        template_file = "aretomo3.sh.j2"

        logger.info(f"Loading AreTomo3 template from: {template_dir}/{template_file}")

        if not os.path.exists(os.path.join(template_dir, template_file)):
            raise FileNotFoundError(f"Template not found: {template_dir}/{template_file}")

        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_file)

        # Get structured template context (schema-driven approach)
        context = self.get_template_context(params, run_context)

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

        # Add old-style CLI args string for backwards compatibility
        cli_variable_args = self.generate_cli_arguments(params)
        template_vars["cli_variable_args"] = cli_variable_args

        # Add structured context for new Jinja loop-based template
        template_vars["context_vars"] = context["context_vars"]
        template_vars["calculated_vars"] = context["calculated_vars"]
        template_vars["schema_vars"] = context["schema_vars"]
        template_vars["control_vars"] = context["control_vars"]
        template_vars["cli_args"] = context["cli_args"]

        # Add SLURM directives (hetjob components)
        template_vars["slurm_directives_component_0"] = context.get("slurm_directives_component_0", [])
        template_vars["slurm_directives_component_1"] = context.get("slurm_directives_component_1", [])

        # Add resolved gain file path (computed, not from schema)
        template_vars["gain_file_path"] = params.get("gain_file_path", "")
        template_vars["gain_is_dm4"] = template_vars["gain_file_path"].endswith(DM4_SUFFIX)

        # Add cluster identifier for cluster-specific template logic
        template_vars["cluster"] = run_context.cluster_id

        # Remote trees come from the DB templates (stores/0022), not literals.
        root = self.get_processing_base_path(cluster=run_context.cluster_id)
        template_vars["out_dir"] = f"{root}/{run_context.msi_session.name}/{run_context.run_number}"
        template_vars["script_dir"] = self.get_script_directory(cluster=run_context.cluster_id)
        template_vars["software_root"] = self.get_software_root(cluster=run_context.cluster_id)
        template_vars["mdoc_dir"] = self._mdoc_dir(run_context.msi_session)

        # Render the template
        rendered_script = template.render(**template_vars)

        logger.info(
            f"Rendered AreTomo3 script for session {run_context.msi_session.name}, run {run_context.run_number}",
        )

        return rendered_script

    def session_defaults(self, msi_session) -> Dict[str, Any]:
        pixel_size = msi_session.get_calibrated_pixel_size()
        return {} if pixel_size is None else {"pixel_size": pixel_size}

    def get_default_slurm_options(self) -> Dict[str, Any]:
        """Get default SLURM options for AreTomo3."""
        return {
            "partition": "gpu",
            "gpus": 8,
            "nodes": 1,
            "cpus_per_task": 16,
            "mem_per_gpu": "96G",
            "time": "140:00:00",
        }

    def get_hetjob_info(self) -> Dict[str, Any]:
        """
        Return heterogeneous job metadata for AreTomo3.

        AreTomo3 uses a heterogeneous job with two components:
        - Component 0: GPU processing (AreTomo3 reconstruction)
        - Component 1: CPU processing (reformatting and metrics)

        Returns:
            Dict with het-group component information
        """
        return {
            "is_heterogeneous": True,
            "components": [
                {
                    "het_group": 0,
                    "name": "aretomo3_gpu",
                    "partition": "gpu",
                    "description": "AreTomo3 tomographic reconstruction on GPU",
                    "gpus": 8,
                    "cpus": 16,
                    "mem_per_gpu": "96G",
                },
                {
                    "het_group": 1,
                    "name": "reformat_cpu",
                    "partition": "cpu",
                    "description": "Reformat, rechunk, and generate metrics",
                    "mem_per_cpu": "196G",
                },
            ],
        }

    def on_job_submit(self, run_context: "RunContext", job_id: str) -> None:
        """
        Hook called after successful job submission.

        Triggers the AreTomo3 syncer to track job progress and sync outputs.

        Args:
            run_context: Execution context
            job_id: SLURM job ID
        """
        # Start AreTomo3 syncer as Django-Q task to monitor for output files
        # Note: base_path defaults to get_processing_base_path() in BaseProcessor
        self._start_syncer_task(
            syncer_class_path="workflow.processors.aretomo3.syncer.AretomoSyncer",
            run_context=run_context,
            job_id=job_id,
        )

    def on_job_complete(self, run_context: "RunContext", success: bool) -> None:
        """
        Hook called when job completes.

        Args:
            run_context: Execution context
            success: True if job completed successfully, False if failed
        """
        if success:
            logger.info(
                f"AreTomo3 job completed successfully for session {run_context.msi_session.name}, "
                f"run {run_context.run_number}",
            )
        else:
            logger.warning(
                f"AreTomo3 job failed for session {run_context.msi_session.name}, run {run_context.run_number}",
            )


# Register the processor after the class is fully defined to avoid circular imports
from workflow.processors import register_processor

register_processor(AreTomo3Processor)
