"""
AreTomo3 Processor

Handles execution of AreTomo3 tomographic reconstruction jobs.
Supports both basic and advanced parameter configurations.
"""

import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from umbrella_logger import logger
from workflow.context import RunContext
from workflow.processors.aretomo3.gain_file_fetcher import DEFAULT_GAIN_DIRECTORY, list_gain_files
from workflow.processors.base import BaseProcessor

# Import register_processor here to avoid circular import
# (it will be called at module import time but after the class is defined)


class AreTomo3Processor(BaseProcessor):
    """Processor for AreTomo3 tomographic reconstruction."""

    name = "aretomo3"
    display_name = "AreTomo3"
    version = "2.2.9"
    cluster = "czii"
    allowed_clusters = ["czii", "bruno"]
    task_name = "tomographic_reconstruction"

    def _calculate_auto_binning(self, pixel_size: float) -> Dict[str, float]:
        """
        Calculate auto-binning factors based on pixel size.

        Computes binning factors to achieve target resolutions:
        - tomo_bin_5A: binning for 5Å tomogram
        - tomo_bin_10A: binning for 10Å tomogram

        Args:
            pixel_size: Calibrated pixel size in Angstroms

        Returns:
            Dict with tomo_bin_5A and tomo_bin_10A values

        Example:
            pixel_size=1.54 → {"tomo_bin_5A": 3.25, "tomo_bin_10A": 6.49}
        """
        return {
            "tomo_bin_5A": round(5 / pixel_size, 2),
            "tomo_bin_10A": round(10 / pixel_size, 2),
        }

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
                binning = self._calculate_auto_binning(float(pixel_size))
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

        # Validate EerSampling and McBin pairing
        eer_sampling = int(params.get("eer_sampling", 2))
        mc_bin = int(params.get("mc_bin", 2))

        if (eer_sampling == 2 and mc_bin != 2) or (eer_sampling == 1 and mc_bin != 1):
            errors.append(
                f"EerSampling and McBin must be paired correctly:\n"
                f"  - Use EerSampling=2 with McBin=2 (super-res extraction with Fourier cropping)\n"
                f"  - Use EerSampling=1 with McBin=1 (Fourier zero-padding upsampling)\n"
                f"Current values: EerSampling={eer_sampling}, McBin={mc_bin}",
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
        Resolve file paths - support both filename and full paths.

        Handles hybrid path format for defect files, dark references, etc.
        - If value starts with '/', treat as absolute path
        - Otherwise, resolve relative to gain reference directory

        Args:
            value: Filename or full path
            params: All parameters

        Returns:
            Resolved absolute path, or empty string if value is empty

        Example:
            "defect.txt" → "/hpc/projects/group.czii/krios1.processing/gain_references/defect.txt"
            "/custom/path/defect.txt" → "/custom/path/defect.txt"
        """
        if not value or str(value).strip() == "":
            return ""

        value_str = str(value).strip()

        # If absolute path, use as-is
        if value_str.startswith("/"):
            return value_str

        # Otherwise, resolve relative to gain reference directory
        # This matches the pattern used for gain files
        gain_dir = "/hpc/projects/group.czii/krios1.processing/gain_references"
        return f"{gain_dir}/{value_str}"

    def _format_cli_at_bin_auto(self, value: Any, params: Dict[str, Any]) -> str:
        """
        Format -AtBin parameter with auto-calculation when empty.

        If at_bin has a user-provided value, use it directly.
        If at_bin is empty, auto-calculate binning factors based on pixel_size:
        - First tomogram: binning for 5Å (5 / pixel_size)
        - Second tomogram: binning for 10Å (10 / pixel_size)
        - Third tomogram: binning for 10Å (10 / pixel_size)

        Args:
            value: User-provided at_bin value (may be empty string)
            params: All parameters (must include pixel_size)

        Returns:
            Formatted string with 1 or 3 binning factors

        Example:
            value="" with pixel_size=1.54 → "3.25 6.49 6.49"
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
            binning = self._calculate_auto_binning(float(pixel_size))
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
        pixel_size = float(params["pixel_size"])
        binning = self._calculate_auto_binning(pixel_size)
        return {
            "tomo_bin_5A": binning["tomo_bin_5A"],
            "tomo_bin_10A": binning["tomo_bin_10A"],
            "slurm_component_0_gpus": int(params.get("slurm_component_0_gpus", 8)),
        }

    def _resolve_gain_file_path(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve gain file path for the template.

        If gain_file_name is empty, fetches the most recent gain file from the cluster.
        Builds the full path by combining the gain directory with the filename.

        Args:
            params: User-provided parameters

        Returns:
            Updated params dict with gain_file_path (full path to gain file)
        """
        params = params.copy()  # Don't mutate original

        gain_file_name = params.get("gain_file_name", "").strip()
        if not gain_file_name:
            # Fetch most recent gain file from cluster
            logger.info("No gain file specified, fetching most recent from cluster")
            result = list_gain_files(cluster_id="czii")

            if result["success"] and result["files"]:
                gain_file_name = result["files"][0]["filename"]
                logger.info(f"Resolved gain file to most recent: {gain_file_name}")
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Failed to fetch gain files from cluster: {error_msg}")
                raise ValueError(
                    f"No gain file specified and failed to fetch from cluster: {error_msg}",
                )

        # Build full path
        gain_file_path = os.path.join(DEFAULT_GAIN_DIRECTORY, gain_file_name)
        params["gain_file_path"] = gain_file_path
        logger.info(f"Gain file path: {gain_file_path}")

        return params

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
        params = self._resolve_gain_file_path(params)

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

        # Render the template
        rendered_script = template.render(**template_vars)

        logger.info(
            f"Rendered AreTomo3 script for session {run_context.msi_session.name}, run {run_context.run_number}",
        )

        return rendered_script

    def parse_output_paths(self, run_context: "RunContext") -> List[Dict[str, str]]:
        """
        Define expected output paths for AreTomo3.

        Args:
            run_context: Execution context

        Returns:
            List of output path specifications
        """
        base_path = f"/hpc/projects/group.czii/krios1.processing/aretomo3/{run_context.msi_session.name}/{run_context.run_number}"

        return [
            {
                "type": "rec",  # Reconstruction volumes
                "pattern": f"{base_path}/vol*/Position_*_Vol.mrc",
            },
            {
                "type": "aln",  # Alignment data
                "pattern": f"{base_path}/Position_*.aln",
            },
            {
                "type": "meta",  # Session metadata JSON
                "pattern": f"{base_path}/AreTomo3_Session.json",
            },
            {
                "type": "log",  # Job output logs
                "pattern": f"{base_path}/JOB*.out",
            },
        ]

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
