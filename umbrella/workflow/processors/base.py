"""
Base Processor Class

Defines the abstract interface that all processing software integrations must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml
from django.core.exceptions import ImproperlyConfigured
from umbrella_logger import logger

from workflow.context import RunContext

if TYPE_CHECKING:
    from tem.models import MsiSession, SessionPlan

# Parsed schema per file
_SCHEMA_CACHE: Dict[Path, Dict[str, Any]] = {}


class BaseProcessor(ABC):
    """
    Abstract base class for all processing software integrations.

    Each processor represents a specific software package (e.g., AreTomo3, DenoisET)
    and knows how to:
    - Validate parameters
    - Render job submission scripts
    - Define expected outputs
    - Handle post-completion tasks

    Subclasses must define these class attributes:
        name: str - Unique identifier (e.g., "aretomo3")
        display_name: str - Human-readable name (e.g., "AreTomo3")
        version: str - Software version
        cluster: str - Default cluster ("czii" or "bruno")

    Example:
        @register_processor
        class AreTomo3Processor(BaseProcessor):
            name = "aretomo3"
            display_name = "AreTomo3"
            version = "2024-03-10"
            cluster = "czii"

            def get_parameter_schema(self):
                return {...}

            def render_script(self, params, run_context):
                return "#!/bin/bash\\n..."
    """

    # Class attributes that must be defined by subclasses
    name: Optional[str] = None
    display_name: Optional[str] = None
    version: Optional[str] = None
    cluster: Optional[str] = None

    # Set to True for processors that should not appear in processor dropdown
    # (e.g., copick-add-object which is accessed via Copick form's Add Object tab)
    # Note: This only affects list_available_processors API. Hidden processors can
    # still be executed via get_processor() and have their DB records synced.
    hidden_from_list: bool = False

    @classmethod
    def _get_schema_file_path(cls) -> Optional[Path]:
        """
        Get path to schema.yaml file for this processor.

        Returns:
            Path to schema.yaml if it exists, None otherwise

        Example:
            For AreTomo3Processor in workflow/processors/aretomo3/processor.py,
            returns workflow/processors/aretomo3/schema.yaml
        """
        # Get the directory containing the processor class module
        import inspect

        processor_file = inspect.getfile(cls)
        processor_dir = Path(processor_file).parent
        schema_path = processor_dir / "schema.yaml"

        return schema_path if schema_path.exists() else None

    @classmethod
    def _load_schema_from_yaml(cls) -> Optional[Dict[str, Any]]:
        """
        Load parameter schema from YAML file.

        Returns:
            Schema dict if YAML file exists and is valid, None otherwise

        Example:
            Schema YAML structure:
            ```yaml
            type: object
            properties:
              pixel_size:
                type: number
                title: Pixel Size (Å)
                description: Pixel size in angstroms
                minimum: 0.5
                maximum: 10.0
                default: 2.5
                x-bash-var: pix_size
                x-bash-format: unquoted
                x-bash-type: number
                x-cli-flag: "-PixSize"
                x-cli-format: direct
            required:
              - pixel_size
            ```
        """
        schema_path = cls._get_schema_file_path()
        if not schema_path:
            return None

        cached = _SCHEMA_CACHE.get(schema_path)
        if cached:
            return cached

        try:
            with open(schema_path, "r") as f:
                schema = yaml.safe_load(f)
            _SCHEMA_CACHE[schema_path] = schema
            logger.debug(f"Loaded schema from {schema_path} for processor {cls.name}")
            return schema
        except Exception as e:
            logger.error(
                f"Error loading schema from {schema_path} for processor {cls.name}: {e}",
                exc_info=True,
            )
            return None

    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Return JSON Schema describing the parameters this processor accepts.

        By default, this method attempts to load the schema from a schema.yaml
        file located in the same directory as the processor class. If no YAML
        file is found, subclasses must override this method to return the schema
        programmatically.

        The schema is used for:
        - Frontend form generation
        - Parameter validation
        - API documentation

        Returns:
            Dict following JSON Schema specification:
            {
                "type": "object",
                "properties": {
                    "param_name": {
                        "type": "number",
                        "title": "Display Name",
                        "description": "Help text",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 50
                    },
                    ...
                },
                "required": ["param_name", ...]
            }

        Example:
            {
                "type": "object",
                "properties": {
                    "pixel_size": {
                        "type": "number",
                        "title": "Pixel Size (Å)",
                        "minimum": 0.5,
                        "maximum": 10.0
                    },
                    "use_gpu": {
                        "type": "boolean",
                        "title": "Use GPU Acceleration",
                        "default": True
                    }
                },
                "required": ["pixel_size"]
            }
        """
        # Try loading from YAML first
        schema = self._load_schema_from_yaml()
        if schema:
            return schema

        # If no YAML file, subclass must override this method
        raise NotImplementedError(
            f"{self.__class__.__name__} must either provide a schema.yaml file "
            f"or override get_parameter_schema() method"
        )

    @abstractmethod
    def render_script(self, params: Dict[str, Any], run_context: "RunContext") -> str:
        """
        Render a bash script for SLURM submission.

        Args:
            params: User-provided parameters (validated against schema)
            run_context: Execution context with session info, inputs, paths

        Returns:
            Complete bash script as string (including shebang)

        Example:
            #!/bin/bash
            #SBATCH --job-name=aretomo3_run001
            #SBATCH --partition=cpu
            #SBATCH --nodes=1

            module load aretomo3/2024-03-10

            aretomo3 -InMrc ${INPUT} -OutMrc ${OUTPUT} ...
        """
        pass

    @abstractmethod
    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters beyond JSON Schema validation.

        Override this method to add custom validation logic that can't be
        expressed in JSON Schema (e.g., conditional requirements, cross-field
        validation).

        Args:
            params: User-provided parameters

        Returns:
            List of error messages (empty list if valid)

        Example:
            def validate_parameters(self, params):
                errors = []

                if params.get('use_old_gain') and not params.get('gain_file'):
                    errors.append("gain_file required when use_old_gain is true")

                if params['binning'] > params['max_binning']:
                    errors.append("binning cannot exceed max_binning")

                return errors
        """
        return []

    def validate_slurm_resources(
        self,
        params: Dict[str, Any],
        cluster_id: str,
    ) -> List[str]:
        """
        Validate SLURM resource parameters against cluster-specific limits.

        This method checks SLURM parameters from the schema (x-slurm-directive)
        against known cluster limits to catch errors before submission.

        Args:
            params: User-provided parameters
            cluster_id: Target cluster ('czii', 'bruno', etc.)

        Returns:
            List of error messages (empty if valid)

        Example validation errors:
            - "GPU count exceeds cluster maximum (requested: 16, max: 8)"
            - "Time limit exceeds cluster maximum (requested: 200:00:00, max: 168:00:00)"
            - "Partition 'himem' not available on cluster 'czii'"
        """
        # Define cluster-specific limits
        CLUSTER_LIMITS = {
            "czii": {
                "max_gpus": 8,
                "max_time_hours": 168,  # 7 days
                "allowed_partitions": ["gpu", "cpu"],
                "max_cpus_per_task": 64,
            },
            "bruno": {
                "max_gpus": 4,
                "max_time_hours": 168,  # 7 days
                "allowed_partitions": ["gpu", "cpu"],
                "max_cpus_per_task": 32,
            },
        }

        errors = []
        limits = CLUSTER_LIMITS.get(cluster_id, {})

        if not limits:
            # Unknown cluster, skip validation
            return errors

        schema = self.get_parameter_schema()

        for param_name, prop in schema.get("properties", {}).items():
            # Only validate SLURM directive parameters
            if not prop.get("x-slurm-directive"):
                continue

            value = params.get(param_name)
            if value is None:
                value = prop.get("default")
            if value is None:
                continue

            directive = prop.get("x-slurm-directive")
            component = prop.get("x-hetjob-component")
            component_label = f" (Component {component})" if component is not None else ""

            # Validate GPU count
            if directive == "--gpus":
                max_gpus = limits.get("max_gpus", 999)
                if int(value) > max_gpus:
                    errors.append(
                        f"GPU count exceeds cluster maximum{component_label}: "
                        f"requested {value}, max {max_gpus} on {cluster_id}",
                    )

            # Validate CPUs per task
            elif directive == "--cpus-per-task":
                max_cpus = limits.get("max_cpus_per_task", 999)
                if int(value) > max_cpus:
                    errors.append(
                        f"CPU count exceeds cluster maximum{component_label}: "
                        f"requested {value}, max {max_cpus} on {cluster_id}",
                    )

            # Validate partition
            elif directive == "--partition":
                allowed_partitions = limits.get("allowed_partitions", [])
                if allowed_partitions and value not in allowed_partitions:
                    errors.append(
                        f"Partition '{value}' not available{component_label} on {cluster_id}. "
                        f"Allowed: {', '.join(allowed_partitions)}",
                    )

            # Validate time limit
            elif directive == "--time":
                max_hours = limits.get("max_time_hours")
                if max_hours:
                    # Parse HH:MM:SS format
                    try:
                        parts = value.split(":")
                        hours = int(parts[0])
                        if len(parts) > 1:
                            hours += int(parts[1]) / 60
                        if len(parts) > 2:
                            hours += int(parts[2]) / 3600

                        if hours > max_hours:
                            errors.append(
                                f"Time limit exceeds cluster maximum{component_label}: "
                                f"requested {value} (~{hours:.1f}h), max {max_hours}h on {cluster_id}",
                            )
                    except (ValueError, IndexError):
                        errors.append(
                            f"Invalid time format{component_label}: {value} (expected HH:MM:SS)",
                        )

        return errors

    @abstractmethod
    def on_job_submit(self, run_context: "RunContext", job_id: str) -> None:
        """
        Hook called immediately after successful job submission.

        Use this to trigger any follow-up actions like:
        - Starting monitoring processes
        - Sending notifications
        - Creating additional database records

        Args:
            run_context: Execution context
            job_id: SLURM job ID

        Example:
            def on_job_submit(self, run_context, job_id):
                # Start syncer process
                subprocess.Popen([
                    'python', 'syncers.py',
                    '--job-id', job_id,
                    '--session', run_context.msi_session.name
                ])
        """
        pass

    @abstractmethod
    def on_job_complete(self, run_context: "RunContext", success: bool) -> None:
        """
        Hook called when job completes (success or failure).

        Use this to:
        - Validate outputs
        - Create result records
        - Clean up temporary files
        - Trigger downstream processing

        Args:
            run_context: Execution context
            success: True if job completed successfully, False if failed

        Example:
            def on_job_complete(self, run_context, success):
                if success:
                    # Create tomogram records from output files
                    self._create_tomogram_records(run_context)
                else:
                    # Send failure notification
                    notify_user(run_context.user, "Processing failed")
        """
        pass

    def _proc_software(self):
        """This processor's ProcSoftware row, or None if it has not synced yet."""
        from processes.models import ProcSoftware

        return ProcSoftware.objects.filter(processor_class=self.name).first()

    def _software_row(self):
        """This processor's ProcSoftware row."""
        row = self._proc_software()
        if row is None:
            raise ImproperlyConfigured(
                f"No ProcSoftware row for processor {self.name!r}; it has not synced yet.",
            )
        return row

    def _resolve_root(self, kind: str, override, dirname: str, cluster=None) -> str:
        from stores.paths import resolve_dir, resolve_template

        context = {"proc_software": dirname}
        if override is not None:
            return resolve_template(override, **context).rstrip("/")
        return resolve_dir(kind, cluster=cluster, **context).rstrip("/")

    def get_script_directory(self, cluster=None) -> str:
        """The remote directory scripts are uploaded to."""
        software = self._software_row()
        return self._resolve_root("script_dir", software.script_dir, software.dirname, cluster)

    def get_processing_base_path(self, cluster=None) -> str:
        """The root this software's runs live under, for every scope (used by syncers)."""
        software = self._software_row()
        return self._resolve_root("processing_root", software.processing_root, software.dirname, cluster)

    def get_software_root(self, cluster=None) -> str:
        """The shared tools tree (executables, conda envs) job scripts reference."""
        from stores.paths import resolve_dir

        return resolve_dir("software_root", cluster=cluster).rstrip("/")

    def get_output_pattern(self, kind: str, plan: Optional["SessionPlan"] = None):
        """The FilePattern naming this software's output files of `kind` (e.g. "rec")."""
        from stores.models import DataKind
        from tem.models import TILT_SERIES_ROLE, resolve_plan_file_pattern

        if not DataKind.objects.filter(data_type=kind).exists():
            raise ImproperlyConfigured(
                f"No DataKind {kind!r} is registered, so no FilePattern can name it. "
                f"Add the kind under Stores → Data kinds first."
            )

        bound = resolve_plan_file_pattern(plan, TILT_SERIES_ROLE) if plan else None
        if bound and bound.data_kind.data_type == kind:
            return bound

        patterns = self._software_row().output_patterns.filter(data_kind__data_type=kind)
        if len(patterns) != 1:
            raise ImproperlyConfigured(
                f"ProcSoftware {self.name!r} needs exactly one {kind!r} output pattern "
                f"(found {len(patterns)}). Bind one under Processes → Proc softwares."
            )
        return patterns[0]

    def session_defaults(self, msi_session: "MsiSession") -> Dict[str, Any]:
        """
        Parameter values derived from the session itself, e.g. a calibrated pixel size.

        Applied last by workflow.defaults.resolve_defaults, on top of the schema
        defaults and the admin-configured ParameterDefaults rows. Return only the
        keys that could actually be derived.
        """
        return {}

    def get_default_slurm_options(self) -> Dict[str, Any]:
        """
        Get default SLURM options for this processor.

        Override to provide processor-specific defaults.

        Returns:
            Dict of SLURM option names to values:
            {
                "partition": "cpu",
                "nodes": 1,
                "ntasks_per_node": 1,
                "mem": "32G",
                "time": "24:00:00"
            }
        """
        return {
            "partition": "cpu",
            "nodes": 1,
            "ntasks_per_node": 1,
            "mem": "16G",
            "time": "24:00:00",
        }

    def get_hetjob_info(self) -> Optional[Dict[str, Any]]:
        """
        Get heterogeneous job metadata if this processor uses SLURM hetjobs.

        Override this method if your processor uses heterogeneous jobs.
        This metadata will be stored in the PipeExecution parameters for tracking.

        Returns:
            Dict with het-group component info, or None if not using hetjobs:
            {
                "is_heterogeneous": True,
                "components": [
                    {
                        "het_group": 0,
                        "name": "gpu_processing",
                        "partition": "gpu",
                        "description": "Main GPU processing"
                    },
                    {
                        "het_group": 1,
                        "name": "cpu_postprocess",
                        "partition": "cpu",
                        "description": "CPU post-processing"
                    }
                ]
            }

        Example:
            def get_hetjob_info(self):
                return {
                    "is_heterogeneous": True,
                    "components": [
                        {"het_group": 0, "name": "aretomo3_gpu", "partition": "gpu"},
                        {"het_group": 1, "name": "reformat_cpu", "partition": "cpu"}
                    ]
                }
        """
        return None

    def get_paths_used(self, run_context: "RunContext") -> Dict[str, Any]:
        """Snapshot of what path resolution produced at submit time."""
        from tem.models import TILT_SERIES_ROLE, resolve_plan_file_pattern

        session = run_context.msi_session
        plan = session.session_plan if session else None
        bound = resolve_plan_file_pattern(plan, TILT_SERIES_ROLE) if plan else None

        kinds = {
            pattern.data_kind.data_type for pattern in self._software_row().output_patterns.select_related("data_kind")
        }
        if bound:
            kinds.add(bound.data_kind.data_type)

        return {
            "processing_base_path": self.get_processing_base_path(cluster=run_context.cluster_id),
            "output_patterns": {kind: self.get_output_pattern(kind, plan=plan).label for kind in kinds},
        }

    def get_database_metadata(self) -> Dict[str, Any]:
        """
        Return metadata for auto-creating/updating ProcSoftware and Task database records.

        This method extracts processor configuration from class attributes to
        automatically synchronize database records on server startup, eliminating
        the need for manual management commands.

        Returns:
            Dict with database fields:
            {
                'name': 'aretomo3',
                'version': '2.2.2_07-11-2025',
                'processor_class': 'aretomo3',
                'default_cluster': 'czii',
                'allowed_clusters': ['czii', 'bruno'],
                'task_name': 'tomographic_reconstruction'
            }

        Example:
            # In workflow/apps.py ready():
            for processor_class in list_processors().values():
                processor = processor_class()
                metadata = processor.get_database_metadata()
                # Create/update ProcSoftware and Task records from metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "processor_class": self.name,
            "default_cluster": self.cluster,
            "allowed_clusters": getattr(self, "allowed_clusters", [self.cluster]),
            "task_name": getattr(self, "task_name", None),
        }

    @classmethod
    def get_views_module(cls):
        """
        Get the custom views module for this processor if it exists.

        Processors can provide custom API views by creating a views.py file
        in their directory. This module can define processor-specific endpoints
        for:
        - Dynamic form field options (dropdown values based on session/context)
        - Custom parameter validation (pre-submission checks)
        - Session-specific defaults (recommended parameter values)
        - Processor metadata (help text, examples, documentation links)

        Returns:
            Module object if views.py exists, None otherwise

        Example:
            processor = AreTomo3Processor()
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, 'get_dynamic_options'):
                options = views_module.get_dynamic_options(request, session_id)
        """
        import importlib
        import inspect
        from pathlib import Path

        try:
            # Get the directory containing the processor class module
            processor_file = inspect.getfile(cls)
            processor_dir = Path(processor_file).parent
            views_path = processor_dir / "views.py"

            if not views_path.exists():
                return None

            # Import the views module dynamically
            # Convert path to module notation: workflow.processors.aretomo3.views
            module_parts = ["workflow", "processors", cls.name, "views"]
            module_name = ".".join(module_parts)

            views_module = importlib.import_module(module_name)
            logger.debug(f"Loaded custom views module for processor {cls.name}")
            return views_module

        except Exception as e:
            logger.warning(
                f"Failed to load views module for processor {cls.name}: {e}",
                exc_info=True,
            )
            return None

    @classmethod
    def has_custom_views(cls) -> bool:
        """
        Check if this processor has a custom views module.

        Returns:
            True if processor has views.py with custom endpoints, False otherwise

        Example:
            if AreTomo3Processor.has_custom_views():
                # Use processor-specific API endpoints
                views = AreTomo3Processor.get_views_module()
                options = views.get_dynamic_options(...)
        """
        return cls.get_views_module() is not None

    # Schema-Driven Template Generation Methods

    def _get_param_bash_var(self, param_name: str) -> Optional[str]:
        """
        Get bash variable name for a schema parameter.

        Args:
            param_name: Parameter name from schema

        Returns:
            Bash variable name or None if parameter is control-flow only

        Example:
            Schema param "pixel_size" with x-bash-var="pix_size" returns "pix_size"
        """
        schema = self.get_parameter_schema()
        prop = schema.get("properties", {}).get(param_name, {})

        # Control-flow params don't map to bash variables
        if prop.get("x-control-flow", False):
            return None

        return prop.get("x-bash-var", param_name)

    def _get_param_cli_flag(self, param_name: str) -> Optional[str]:
        """
        Get CLI flag for a schema parameter.

        Args:
            param_name: Parameter name from schema

        Returns:
            CLI flag (e.g., "-PixSize") or None if not applicable

        Example:
            Schema param "pixel_size" with x-cli-flag="-PixSize" returns "-PixSize"
            Control-flow params return None
        """
        schema = self.get_parameter_schema()
        prop = schema.get("properties", {}).get(param_name, {})

        # Control-flow params don't have CLI flags
        if prop.get("x-control-flow", False):
            return None

        # Parameters that are part of composite flags return None
        if prop.get("x-cli-flag") is None and not prop.get("x-cli-composite"):
            return None

        return prop.get("x-cli-flag")

    def _format_cli_param(self, param_name: str, value: Any, params: Dict[str, Any]) -> str:
        """
        Format a parameter value for CLI usage.

        Args:
            param_name: Parameter name from schema
            value: Parameter value
            params: All parameters (for composite formatting)

        Returns:
            Formatted string for CLI

        Example:
            format_type="direct" → str(value)
            format_type="boolean_to_int" → "1" or "0"
            format_type="custom_formatter" → calls _format_cli_custom_formatter()
        """
        schema = self.get_parameter_schema()
        prop = schema.get("properties", {}).get(param_name, {})
        format_type = prop.get("x-cli-format", "direct")

        if format_type == "direct":
            return str(value)

        # Call processor-specific formatter method
        formatter_method = f"_format_cli_{format_type}"
        if hasattr(self, formatter_method):
            return getattr(self, formatter_method)(value, params)

        logger.warning(
            f"Unknown CLI format type '{format_type}' for parameter '{param_name}' "
            f"in processor '{self.name}'. Using direct formatting.",
        )
        return str(value)

    def generate_bash_variables(
        self,
        params: Dict[str, Any],
        run_context: "RunContext",
    ) -> Dict[str, Any]:
        """
        Generate dictionary of bash variables from schema and parameters.

        This method uses the parameter schema to automatically extract
        bash variable names and apply defaults, reducing duplication.

        Args:
            params: User-provided parameters
            run_context: Execution context with session, run, user info

        Returns:
            Dict of bash variable names to values, ready for template.render()

        Example:
            schema param "pixel_size" with x-bash-var="pix_size" and value 2.5
            returns {"pix_size": 2.5}

        Notes:
            - Applies defaults from schema if parameter not provided
            - Skips control-flow params (but includes them for template conditionals)
            - Processors can override for complex transformations
        """
        schema = self.get_parameter_schema()
        bash_vars = {}

        for param_name, prop in schema.get("properties", {}).items():
            # Get parameter value with default
            value = params.get(param_name)
            if value is None:
                value = prop.get("default")

            # Get bash variable name
            bash_var_name = self._get_param_bash_var(param_name)

            if bash_var_name is None:
                # Control-flow param - include for template conditionals
                bash_vars[param_name] = value if value is not None else False
            elif isinstance(bash_var_name, list):
                # Multi-variable param (e.g., local_shift → local_aln_1, local_aln_2)
                handler_method = f"_handle_multi_var_{param_name}"
                if hasattr(self, handler_method):
                    multi_vars = getattr(self, handler_method)(value, params)
                    bash_vars.update(multi_vars)
                else:
                    logger.warning(
                        f"Parameter '{param_name}' specifies multi-var {bash_var_name} "
                        f"but no handler method {handler_method}() found in {self.name}",
                    )
            else:
                # Single bash variable
                if value is not None:
                    bash_vars[bash_var_name] = value

        return bash_vars

    def generate_cli_arguments(self, params: Dict[str, Any]) -> str:
        """
        Generate CLI argument string from parameters based on schema.

        This method uses the schema's x-cli-flag and x-cli-format properties
        to automatically build the command-line arguments string.

        Only includes parameters that have user-provided values different from
        the schema default, unless marked with x-cli-always-include or required.

        Args:
            params: User-provided parameters

        Returns:
            Formatted CLI arguments as multi-line string with backslash continuations

        Example:
            Returns:
            "    -PixSize 2.5 \\
                -TotalDose 120 \\
                -FmDose 1.5"

        Notes:
            - Skips parameters without x-cli-flag
            - Applies formatters specified in x-cli-format
            - Only includes non-default values (uses generate_cli_arguments_structured)
        """
        # Use structured method and format as string
        cli_args = self.generate_cli_arguments_structured(params)
        args = [f"    {arg['flag']} {arg['value']}" for arg in cli_args]
        return " \\\n".join(args)

    def validate_schema_cli_mapping(self) -> List[str]:
        """
        Validate that schema CLI mapping is complete and correct.

        Checks that:
        - All non-control-flow params have x-cli-flag (or are composite)
        - All params with custom x-cli-format have corresponding formatter methods
        - All multi-var params have handler methods

        Returns:
            List of validation issues (empty if valid)

        Example:
            issues = processor.validate_schema_cli_mapping()
            if issues:
                for issue in issues:
                    print(f"Warning: {issue}")
        """
        schema = self.get_parameter_schema()
        issues = []

        for param_name, prop in schema.get("properties", {}).items():
            # Skip control-flow params
            if prop.get("x-control-flow", False):
                continue

            # Check if x-cli-flag is defined (unless it's part of composite)
            if "x-cli-flag" not in prop and not prop.get("x-cli-composite"):
                issues.append(f"Parameter '{param_name}' missing x-cli-flag")

            # Check if x-cli-format is defined (None is acceptable for params without CLI flags)
            if "x-cli-format" not in prop and prop.get("x-cli-flag") is not None:
                issues.append(f"Parameter '{param_name}' missing x-cli-format")

            # If custom format, check formatter method exists
            format_type = prop.get("x-cli-format")
            if format_type and format_type != "direct":
                formatter_method = f"_format_cli_{format_type}"
                if not hasattr(self, formatter_method):
                    issues.append(
                        f"Parameter '{param_name}' specifies format '{format_type}' "
                        f"but method {formatter_method}() not found",
                    )

            # Check multi-var params have handlers
            bash_var = prop.get("x-bash-var")
            if isinstance(bash_var, list):
                handler_method = f"_handle_multi_var_{param_name}"
                if not hasattr(self, handler_method):
                    issues.append(
                        f"Parameter '{param_name}' specifies multi-var {bash_var} "
                        f"but method {handler_method}() not found",
                    )

        return issues

    # Schema-Driven Template Generation - Structured Methods

    def generate_bash_variables_structured(
        self,
        params: Dict[str, Any],
        run_context: "RunContext",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate structured bash variables with metadata for template loops.

        Returns bash variables with rendering metadata specified in the schema.
        This enables templates to use Jinja loops to dynamically generate bash
        variable declarations based on x-bash-format and x-bash-type properties.

        Args:
            params: User-provided parameters
            run_context: Execution context

        Returns:
            Dict mapping bash variable names to metadata dicts:
            {
                "pix_size": {
                    "value": 2.5,
                    "format": "quoted",  # from x-bash-format
                    "type": "number",    # from x-bash-type
                },
                ...
            }

        Example template usage:
            {% for var_name, var_info in schema_vars.items() %}
            {% if var_info.format == "quoted" %}
            {{ var_name }}="{{ var_info.value }}"
            {% elif var_info.format == "unquoted" %}
            {{ var_name }}={{ var_info.value }}
            {% endif %}
            {% endfor %}
        """
        schema = self.get_parameter_schema()
        structured_vars = {}

        for param_name, prop in schema.get("properties", {}).items():
            # Skip if x-bash-skip is True (control-flow params)
            if prop.get("x-bash-skip", False):
                continue

            # Get parameter value with default
            value = params.get(param_name)
            if value is None:
                value = prop.get("default")

            # Skip if still None
            if value is None:
                continue

            # Coerce value to schema-declared type
            value = self._coerce_to_schema_type(value, prop)

            # Get bash variable name(s)
            bash_var_name = prop.get("x-bash-var")
            if not bash_var_name:
                continue

            # Get rendering metadata
            bash_format = prop.get("x-bash-format", "quoted")
            bash_type = prop.get("x-bash-type", "string")

            if isinstance(bash_var_name, list):
                # Multi-variable param (e.g., local_shift → local_aln_1, local_aln_2)
                handler_method = f"_handle_multi_var_{param_name}"
                if hasattr(self, handler_method):
                    multi_vars = getattr(self, handler_method)(value, params)
                    for var_name, var_value in multi_vars.items():
                        structured_vars[var_name] = {
                            "value": var_value,
                            "format": bash_format,
                            "type": bash_type,
                        }
            else:
                # Single bash variable
                structured_vars[bash_var_name] = {
                    "value": value,
                    "format": bash_format,
                    "type": bash_type,
                }

        return structured_vars

    def generate_cli_arguments_structured(self, params: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate structured CLI arguments as list of dicts for template loops.

        Only includes parameters when the effective value differs from the CLI tool's
        default (x-cli-default), or when the parameter is required/always-include.

        Schema supports two default types:
        - `default`: Form pre-fill value (what user sees in UI)
        - `x-cli-default`: CLI tool's internal default (what tool uses if flag omitted)

        A flag is included when:
        - Parameter is required, OR
        - Parameter has x-cli-always-include: true, OR
        - Effective value differs from x-cli-default (or default if x-cli-default not set)

        Args:
            params: User-provided parameters

        Returns:
            List of argument dicts:
            [
                {"flag": "-PixSize", "value": "2.5"},
                {"flag": "-TotalDose", "value": "120"},
                ...
            ]

        Example template usage:
            {% for arg in cli_args %}
            {{ arg.flag }} {{ arg.value }} \
            {% endfor %}
        """
        schema = self.get_parameter_schema()
        required_params = set(schema.get("required", []))
        cli_args = []

        for param_name, prop in schema.get("properties", {}).items():
            # Skip control-flow params and composite sub-params
            if prop.get("x-control-flow", False) or prop.get("x-cli-composite") is True:
                continue

            # Get CLI flag
            cli_flag = prop.get("x-cli-flag")
            if not cli_flag:
                continue

            # Get values:
            # - user_value: what user provided (or None)
            # - schema_default: form pre-fill value
            # - cli_default: CLI tool's internal default (falls back to schema_default)
            user_value = params.get(param_name)
            schema_default = prop.get("default")
            cli_default = prop.get("x-cli-default", schema_default)  # CLI default, or schema default if not specified

            is_required = param_name in required_params
            always_include = prop.get("x-cli-always-include", False)

            # Determine effective value (user value or schema default)
            if user_value is not None:
                effective_value = user_value
            elif schema_default is not None:
                effective_value = schema_default
            else:
                effective_value = None

            # Coerce value to schema-declared type
            effective_value = self._coerce_to_schema_type(effective_value, prop)

            # Determine if we should include this argument
            if is_required or always_include:
                # Always include required params and always-include params
                if effective_value is None:
                    continue  # Skip if no value at all
                value = effective_value
            else:
                # Optional param - only include if effective value differs from CLI default
                if effective_value is None:
                    continue  # No value to include

                # Skip if effective value equals the CLI default
                if self._values_equal(effective_value, cli_default):
                    continue  # Skip - CLI tool will use its own default

                value = effective_value

            # Format the value
            formatted_value = self._format_cli_param(param_name, value, params)

            # Skip empty formatted values (e.g., empty strings)
            if formatted_value == "" or formatted_value is None:
                continue

            # Add to args list
            cli_args.append(
                {
                    "flag": cli_flag,
                    "value": formatted_value,
                }
            )

        return cli_args

    def _coerce_to_schema_type(self, value: Any, prop: Dict[str, Any]) -> Any:
        """Coerce a parameter value to its schema-declared type."""
        if value is None:
            return None
        param_type = prop.get("type")
        if param_type == "integer":
            return int(value)
        elif param_type == "number":
            return float(value)
        elif param_type == "boolean" and isinstance(value, str):
            return value.lower() not in ("false", "0", "")
        return value

    def _values_equal(self, value1: Any, value2: Any) -> bool:
        """
        Compare two values for equality, handling type differences.

        Handles cases like comparing "2" (str) with 2 (int), or "true" with True.
        """
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False

        # Try direct comparison first
        if value1 == value2:
            return True

        # Handle string/number comparisons
        try:
            # Try numeric comparison
            if isinstance(value1, (int, float)) or isinstance(value2, (int, float)):
                return float(value1) == float(value2)
        except (ValueError, TypeError):
            pass

        # Handle boolean/string comparisons
        if isinstance(value1, bool) or isinstance(value2, bool):
            str1 = str(value1).lower()
            str2 = str(value2).lower()
            bool_map = {"true": True, "false": False, "1": True, "0": False}
            if str1 in bool_map and str2 in bool_map:
                return bool_map[str1] == bool_map[str2]

        # String comparison as fallback
        return str(value1) == str(value2)

    def get_calculated_vars(
        self,
        params: Dict[str, Any],
        run_context: "RunContext",
    ) -> Dict[str, Any]:
        """
        Get processor-specific calculated variables.

        Override this method in subclasses to provide calculated variables
        that are derived from parameters but not directly from the schema.

        Args:
            params: User-provided parameters
            run_context: Execution context

        Returns:
            Dict of calculated variable names to values

        Example (AreTomo3):
            def get_calculated_vars(self, params, run_context):
                pixel_size = float(params['pixel_size'])
                return {
                    'tomo_bin_5A': round(5 / pixel_size, 2),
                    'tomo_bin_10A': round(10 / pixel_size, 2),
                }
        """
        return {}

    def generate_slurm_directives(
        self,
        params: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Generate SLURM directives from schema parameters for regular (non-hetjob) jobs.

        Extracts parameters with x-slurm-directive extension and formats them
        for template rendering.

        Args:
            params: User-provided parameters

        Returns:
            List of directive dicts:
            [
                {"directive": "--partition", "value": "gpu"},
                {"directive": "--gpus", "value": "8"},
                {"directive": "--time", "value": "140:00:00"},
                ...
            ]

        Example template usage:
            {% for directive in slurm_directives %}
            #SBATCH {{ directive.directive }}={{ directive.value }}
            {% endfor %}
        """
        schema = self.get_parameter_schema()
        directives = []

        for param_name, prop in schema.get("properties", {}).items():
            # Only process parameters with x-slurm-directive extension
            slurm_directive = prop.get("x-slurm-directive")
            if not slurm_directive:
                continue

            # Skip hetjob-specific parameters (those are handled separately)
            if prop.get("x-hetjob-component") is not None:
                continue

            # Get parameter value with default fallback
            # Try with schema field name first (e.g., slurm_partition)
            value = params.get(param_name)

            # Fallback: try without slurm_ prefix for compatibility (e.g., partition)
            if value is None and param_name.startswith("slurm_"):
                fallback_name = param_name[6:]  # Remove 'slurm_' prefix
                value = params.get(fallback_name)

            # Fallback: use schema default
            if value is None:
                value = prop.get("default")
            if value is None:
                continue

            # Skip empty strings (allows users to leave memory settings blank)
            if isinstance(value, str) and value.strip() == "":
                continue

            # Check conditional visibility (e.g., mem-per-gpu only for GPU partition)
            conditional = prop.get("x-conditional")
            if conditional:
                # Simple evaluation: "slurm_partition == 'gpu'"
                if not self._evaluate_conditional(conditional, params):
                    continue

            directives.append(
                {
                    "directive": slurm_directive,
                    "value": str(value),
                }
            )

        return directives

    def generate_slurm_directives_hetjob(
        self,
        params: Dict[str, Any],
    ) -> Dict[int, List[Dict[str, str]]]:
        """
        Generate SLURM directives for heterogeneous jobs (per-component).

        Extracts parameters with x-hetjob-component extension and groups them
        by component number.

        Args:
            params: User-provided parameters

        Returns:
            Dict mapping component number to directives:
            {
                0: [
                    {"directive": "--partition", "value": "gpu"},
                    {"directive": "--gpus", "value": "8"},
                ],
                1: [
                    {"directive": "--partition", "value": "cpu"},
                    {"directive": "--mem-per-cpu", "value": "196G"},
                ],
            }

        Example template usage:
            # Component 0
            {% for directive in slurm_directives_component_0 %}
            #SBATCH {{ directive.directive }}={{ directive.value }}
            {% endfor %}

            #SBATCH hetjob

            # Component 1
            {% for directive in slurm_directives_component_1 %}
            #SBATCH {{ directive.directive }}={{ directive.value }}
            {% endfor %}
        """
        schema = self.get_parameter_schema()
        component_directives = {}

        for param_name, prop in schema.get("properties", {}).items():
            # Only process parameters with x-slurm-directive extension
            slurm_directive = prop.get("x-slurm-directive")
            if not slurm_directive:
                continue

            # Only process hetjob-specific parameters
            hetjob_component = prop.get("x-hetjob-component")
            if hetjob_component is None:
                continue

            # Get parameter value with default fallback
            # Try with schema field name first (e.g., slurm_partition)
            value = params.get(param_name)

            # Fallback: try without slurm_ prefix for compatibility (e.g., partition)
            if value is None and param_name.startswith("slurm_"):
                fallback_name = param_name[6:]  # Remove 'slurm_' prefix
                value = params.get(fallback_name)

            # Fallback: use schema default
            if value is None:
                value = prop.get("default")
            if value is None:
                continue

            # Skip empty strings (allows users to leave memory settings blank)
            if isinstance(value, str) and value.strip() == "":
                continue

            # Check conditional visibility
            conditional = prop.get("x-conditional")
            if conditional:
                if not self._evaluate_conditional(conditional, params):
                    continue

            # Initialize component list if needed
            if hetjob_component not in component_directives:
                component_directives[hetjob_component] = []

            component_directives[hetjob_component].append(
                {
                    "directive": slurm_directive,
                    "value": str(value),
                }
            )

        return component_directives

    def _evaluate_conditional(self, conditional: str, params: Dict[str, Any]) -> bool:
        """
        Evaluate a simple conditional expression for parameter visibility.

        Supports basic comparisons like "slurm_partition == 'gpu'".

        Args:
            conditional: Conditional expression string
            params: User parameters

        Returns:
            True if condition is met, False otherwise
        """
        # Simple parser for "param_name == 'value'" expressions
        if "==" in conditional:
            parts = conditional.split("==")
            if len(parts) == 2:
                param_name = parts[0].strip()
                expected_value = parts[1].strip().strip("'\"")
                actual_value = str(params.get(param_name, ""))
                return actual_value == expected_value

        # Default to True if we can't parse the conditional
        return True

    def get_template_context(
        self,
        params: Dict[str, Any],
        run_context: "RunContext",
    ) -> Dict[str, Any]:
        """
        Generate complete template context with structured data for loops.

        This is the main entry point for template rendering. It combines:
        - schema_vars: User parameters from schema (for Jinja loops)
        - context_vars: Framework-provided variables (run_number, user_id, etc.)
        - calculated_vars: Processor-specific calculations
        - cli_args: Structured CLI arguments (for Jinja loops)
        - control_vars: Control-flow booleans (use_advanced_params, etc.)

        Args:
            params: User-provided parameters
            run_context: Execution context

        Returns:
            Dict with structured template context:
            {
                "schema_vars": {...},     # Variables from schema (with metadata)
                "context_vars": {...},    # Framework-provided
                "calculated_vars": {...}, # Processor calculations
                "cli_args": [...],        # Structured CLI arguments
                "control_vars": {...},    # Boolean flags for conditionals
            }

        Example template usage:
            # Context variables (framework-provided)
            {% for var_name, var_value in context_vars.items() %}
            {{ var_name }}="{{ var_value }}"
            {% endfor %}

            # Schema variables (from parameters)
            {% for var_name, var_info in schema_vars.items() %}
            {% if var_info.format == "quoted" %}
            {{ var_name }}="{{ var_info.value }}"
            {% endif %}
            {% endfor %}

            # CLI arguments
            {% for arg in cli_args %}
            {{ arg.flag }} {{ arg.value }} \
            {% endfor %}
        """
        # Get structured bash variables from schema
        schema_vars = self.generate_bash_variables_structured(params, run_context)

        # Get framework-provided context variables
        context_vars = {
            "project_name": run_context.msi_session.name,
            "run_number": run_context.run_number,
            "user_id": run_context.user.username if hasattr(run_context.user, "username") else str(run_context.user),
            "job_name": run_context.job_name,
        }

        # Get processor-specific calculated variables
        calculated_vars = self.get_calculated_vars(params, run_context)

        # Get structured CLI arguments
        cli_args = self.generate_cli_arguments_structured(params)

        # Get control-flow variables for template conditionals
        schema = self.get_parameter_schema()
        control_vars = {}
        for param_name, prop in schema.get("properties", {}).items():
            if prop.get("x-control-flow", False):
                value = params.get(param_name, prop.get("default", False))
                control_vars[param_name] = value

        # Generate SLURM directives from schema
        # Check if this is a hetjob processor
        hetjob_info = self.get_hetjob_info()
        result = {
            "schema_vars": schema_vars,
            "context_vars": context_vars,
            "calculated_vars": calculated_vars,
            "cli_args": cli_args,
            "control_vars": control_vars,
        }

        if hetjob_info and hetjob_info.get("is_heterogeneous"):
            # Hetjob: generate per-component directives
            component_directives = self.generate_slurm_directives_hetjob(params)
            # Add each component's directives as separate keys
            for component_num, directives in component_directives.items():
                result[f"slurm_directives_component_{component_num}"] = directives
        else:
            # Regular job: single directive list
            result["slurm_directives"] = self.generate_slurm_directives(params)

        return result

    def _start_syncer_task(
        self,
        syncer_class_path: str,
        run_context: "RunContext",
        job_id: str,
        base_path: str = None,
    ) -> str:
        """
        Start a syncer as a Django-Q async task.

        This is the preferred method for processors to start output syncers.
        The syncer will run as a self-rescheduling Django-Q task that polls
        for output files every 5 minutes until the SLURM job completes.

        Args:
            syncer_class_path: Full import path to syncer class
                (e.g., 'workflow.processors.aretomo3.syncer.AretomoSyncer')
            run_context: Execution context with session/run info
            job_id: SLURM job ID
            base_path: Base path for syncer (optional - defaults to get_processing_base_path())
                (e.g., '/hpc/projects/krios1.processing/aretomo3')

        Returns:
            Django-Q task ID (string)

        Example:
            def on_job_submit(self, run_context, job_id):
                # Use default path from get_processing_base_path()
                self._start_syncer_task(
                    'workflow.processors.aretomo3.syncer.AretomoSyncer',
                    run_context,
                    job_id
                )
        """
        from processes.tasks import start_syncer_monitoring

        if base_path is None:
            base_path = self.get_processing_base_path(cluster=run_context.cluster_id)

        try:
            task_id = start_syncer_monitoring(
                syncer_class_path=syncer_class_path,
                base_path=base_path,
                session_name=run_context.msi_session.name,
                run_id=run_context.run_number,
                job_id=job_id,
            )

            logger.info(
                f"Started syncer task for {run_context.msi_session.name}/"
                f"{run_context.run_number} (job {job_id}, task {task_id})",
            )

            return task_id

        except Exception as e:
            logger.error(
                f"Error starting syncer task: {e}",
                exc_info=True,
            )
            return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} version={self.version!r}>"
