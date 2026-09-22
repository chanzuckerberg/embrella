"""
Workflow views submodule.

- constants.py: Module-level constants and configuration
- utils.py: Utility functions used across views
- ssh_views.py: SSH key setup and verification views
- metadata_views.py: Metadata processing and visualization views
- session_views.py: Session lookup endpoints kept at their pre-v1 paths
- job_views.py: Job log retrieval
- job_api.py: Job API endpoints for listing and bulk operations
- execution_api.py: Modern processor-based pipeline execution API
"""

# Import copick-specific views
from workflow.processors.copick.views import (
    get_copick_annotated_count,
    get_copick_runs,
)
from workflow.processors.copick.views import (
    get_template_maps as get_copick_template_maps,
)

# Import and re-export constants
from .constants import (
    KEYS,
    LABEL_TO_SLURM_STATE,
    SLURM_STATE_TO_LABEL,
)

# Import and re-export execution API views
from .execution_api import (
    check_dependencies,
    execute_pipe,
    get_execution_by_job_id,
    get_execution_status,
    get_plan_runs,
    get_processor_defaults,
    get_processor_metadata,
    get_processor_options,
    get_processor_schema,
    list_available_processors,
    list_run_executions,
    lookup_execution_ids,
    preview_script,
    validate_processor_parameters,
    validate_processor_session,
)

# Import and re-export job API views
from .job_api import bulk_cancel_jobs, get_jobs_filterlist, get_jobs_list, get_syncer_logs, rerun_syncer

# Import and re-export job views
from .job_views import get_job_logs

# Import and re-export metadata views
from .metadata_views import get_copick_aretomo_compat, get_metadata_summary, get_metadata_viz_data

# Import and re-export session lookup views
from .session_views import get_aretomo3_json, get_msi_session_list, get_msisession_id

# Import and re-export SSH views
from .ssh_views import check_ssh_setup, setup_ssh_key

# Import and re-export utilities
from .utils import (
    apply_filters,
    calculate_metric_ranges,
    compute_stats,
    format_job_output,
    track_jobs_internal,
)

__all__ = [
    # Constants
    "KEYS",
    "LABEL_TO_SLURM_STATE",
    "SLURM_STATE_TO_LABEL",
    # Utilities
    "apply_filters",
    "calculate_metric_ranges",
    "compute_stats",
    "format_job_output",
    "track_jobs_internal",
    # SSH views
    "check_ssh_setup",
    "setup_ssh_key",
    # Session lookup views
    "get_aretomo3_json",
    "get_msi_session_list",
    "get_msisession_id",
    # Copick views
    "get_copick_runs",
    "get_copick_annotated_count",
    "get_copick_template_maps",
    # Metadata views
    "get_copick_aretomo_compat",
    "get_metadata_summary",
    "get_metadata_viz_data",
    # Job views
    "get_job_logs",
    # Job API views
    "bulk_cancel_jobs",
    "get_jobs_filterlist",
    "get_jobs_list",
    "get_syncer_logs",
    "rerun_syncer",
    # Execution API views
    "check_dependencies",
    "execute_pipe",
    "get_execution_by_job_id",
    "get_execution_status",
    "get_plan_runs",
    "get_processor_defaults",
    "get_processor_metadata",
    "get_processor_options",
    "get_processor_schema",
    "list_available_processors",
    "list_run_executions",
    "lookup_execution_ids",
    "preview_script",
    "validate_processor_parameters",
    "validate_processor_session",
]
