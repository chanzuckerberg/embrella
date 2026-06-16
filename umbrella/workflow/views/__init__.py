"""
Workflow views submodule.

This module contains organized workflow views, constants, and utilities:

MODERN (API-only):
- constants.py: Module-level constants and configuration
- utils.py: Utility functions used across views
- ssh_views.py: SSH key setup and verification views
- metadata_views.py: Metadata processing and visualization views
- job_views.py: Job management and tracking views
- job_api.py: Job API endpoints for listing and bulk operations
- execution_api.py: Modern processor-based pipeline execution API

LEGACY (old patterns - see workflow.legacy):
- template_views.py: Django template rendering views (LEGACY)
- aretomo3_views.py: AreTomo3 agent-based job submission (LEGACY)
- denoiset_views.py: DenoisET agent-based job submission (LEGACY)
- copick_views.py: Copick agent-based job submission (LEGACY)
- dashboard_views.py: Dashboard template rendering (LEGACY)
"""

# Import and re-export LEGACY views (for backward compatibility)
# These use old patterns - see workflow.legacy for details
from workflow.legacy.views.aretomo3_views import get_aretomo3_json, run_aretomo3, run_aretomo3_advanced
from workflow.legacy.views.copick_views import (
    get_template_map_json,
    run_copick_add_object,
    run_create_copick,
    run_import_tomogram_copick,
)
from workflow.legacy.views.dashboard_views import (
    dashboard,
    get_msi_params_list,
    get_msi_session_list,
    get_msisession_id,
    get_plan_id,
    status_check_api,
    trigger_syncer,
    workflow_get_data,
)
from workflow.legacy.views.denoiset_views import run_denoiset
from workflow.legacy.views.template_views import (
    custom_run_membraneseg_page,
    custom_run_octopi_page,
    custom_run_workflow_page,
    custom_workflow_cancel,
    custom_workflow_logs,
    custom_workflow_page,
    custom_workflow_track,
    cutom_run_create_and_import_copick_page,
    cutom_run_denoise_workflow_page,
)

# Import modern copick-specific views
from workflow.processors.copick.views import (
    get_copick_runs,
)
from workflow.processors.copick.views import (
    get_template_maps as get_copick_template_maps,
)

# Import and re-export constants
from .constants import (
    ARETOMO3_BASIC_TEMPLATE_PATH,
    ARETOMO3_SCRIPT_PATH,
    ARETOMO3_TEMPLATE_PATH,
    BASE_DIR,
    COPICK_ADD_OBJECT_TEMPLATE_PATH,
    COPICK_IMPORT_TOMO_TEMPLATE_PATH,
    COPICK_SCRIPT_DIR,
    COPICK_TEMPLATE_PATH,
    DATA_COLLECTION_PATH,
    DENOISET_SCRIPT_PATH,
    DENOISET_TEMPLATE_PATH,
    ENVIRONMENT,
    HOST,
    HOST_BRUNO,
    KEYFILE,
    KEYS,
    LABEL_TO_SLURM_STATE,
    PORT,
    SLURM_STATE_TO_LABEL,
    STATUS_CHECKER_SCRIPT_PATH,
    STATUS_CHECKER_TEMPLATE_PATH,
    USERNAME,
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
from .job_views import cancel_jobs, get_job_logs, track_jobs, user_info

# Import and re-export metadata views
from .metadata_views import get_metadata_summary, get_metadata_viz_data

# Import and re-export SSH views
from .ssh_views import check_ssh_setup, setup_ssh_key

# Import and re-export utilities
from .utils import (
    apply_filters,
    calculate_metric_ranges,
    compute_stats,
    format_job_output,
    get_base_url,
    natural_key,
    natural_position_sort_key,
    parse_script_output,
    preprocess_csv,
    store_log,
    track_jobs_internal,
)

__all__ = [
    # Constants
    "ARETOMO3_BASIC_TEMPLATE_PATH",
    "ARETOMO3_SCRIPT_PATH",
    "ARETOMO3_TEMPLATE_PATH",
    "BASE_DIR",
    "COPICK_ADD_OBJECT_TEMPLATE_PATH",
    "COPICK_IMPORT_TOMO_TEMPLATE_PATH",
    "COPICK_SCRIPT_DIR",
    "COPICK_TEMPLATE_PATH",
    "DATA_COLLECTION_PATH",
    "DENOISET_SCRIPT_PATH",
    "DENOISET_TEMPLATE_PATH",
    "ENVIRONMENT",
    "HOST",
    "HOST_BRUNO",
    "KEYFILE",
    "KEYS",
    "LABEL_TO_SLURM_STATE",
    "PORT",
    "SLURM_STATE_TO_LABEL",
    "STATUS_CHECKER_SCRIPT_PATH",
    "STATUS_CHECKER_TEMPLATE_PATH",
    "USERNAME",
    # Utilities
    "apply_filters",
    "calculate_metric_ranges",
    "compute_stats",
    "format_job_output",
    "get_base_url",
    "natural_key",
    "natural_position_sort_key",
    "parse_script_output",
    "preprocess_csv",
    "store_log",
    "track_jobs_internal",
    # Template views
    "custom_run_membraneseg_page",
    "custom_run_octopi_page",
    "custom_run_workflow_page",
    "custom_workflow_cancel",
    "custom_workflow_logs",
    "custom_workflow_page",
    "custom_workflow_track",
    "cutom_run_create_and_import_copick_page",
    "cutom_run_denoise_workflow_page",
    # SSH views
    "check_ssh_setup",
    "setup_ssh_key",
    # AreTomo3 views
    "get_aretomo3_json",
    "run_aretomo3",
    "run_aretomo3_advanced",
    # DenoisET views
    "run_denoiset",
    # Copick views (legacy)
    "get_template_map_json",
    "run_copick_add_object",
    "run_create_copick",
    "run_import_tomogram_copick",
    # Copick views (modern)
    "get_copick_runs",
    "get_copick_template_maps",
    # Metadata views
    "get_metadata_summary",
    "get_metadata_viz_data",
    # Job views
    "cancel_jobs",
    "get_job_logs",
    "track_jobs",
    "user_info",
    # Job API views
    "bulk_cancel_jobs",
    "get_jobs_filterlist",
    "get_jobs_list",
    "get_syncer_logs",
    "rerun_syncer",
    # Dashboard views
    "dashboard",
    "get_msi_params_list",
    "get_msi_session_list",
    "get_msisession_id",
    "get_plan_id",
    "status_check_api",
    "trigger_syncer",
    "workflow_get_data",
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
