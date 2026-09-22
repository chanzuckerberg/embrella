from django.urls import path

from . import views

app_name = "workflow"

urlpatterns = [
    # Pre-v1 paths the Next.js app still calls (see workflow/views/session_views.py, job_views.py)
    path("get_aretomo3", views.get_aretomo3_json, name="json_aretomo3"),
    path("get_msi_session_list", views.get_msi_session_list, name="get all msi session name"),
    path("get_msisession_id", views.get_msisession_id, name="get_msisession_id"),
    path("job_logs", views.get_job_logs, name="fetching logs"),
    # Job Management API
    path("v1/jobs/", views.get_jobs_list, name="get_jobs_list"),
    path("v1/jobs/filterlist/", views.get_jobs_filterlist, name="get_jobs_filterlist"),
    path("v1/jobs/bulk_cancel/", views.bulk_cancel_jobs, name="bulk_cancel_jobs"),
    path("v1/jobs/<str:job_id>/syncer_logs/", views.get_syncer_logs, name="get_syncer_logs"),
    path("v1/jobs/<str:job_id>/rerun_syncer/", views.rerun_syncer, name="rerun_syncer"),
    # Metadata API
    path("metadata/api/v1/summary/", views.get_metadata_summary, name="get_metadata_summary"),
    path("metadata/api/v1/data/", views.get_metadata_viz_data, name="get_metadata_viz_data"),
    path(
        "metadata/api/v1/copick-compat/",
        views.get_copick_aretomo_compat,
        name="get_copick_aretomo_compat",
    ),
    # SSH Setup API
    path("v1/ssh/check_setup/", views.check_ssh_setup, name="check_ssh_setup"),
    path("v1/ssh/setup_key/", views.setup_ssh_key, name="setup_ssh_key"),
    # Processor-based Execution API (PREFERRED - modern processor system)
    # Use these endpoints for new job submissions instead of legacy agent-based pattern
    path("v1/processors/", views.list_available_processors, name="list_processors"),
    path("v1/processors/<str:processor_name>/schema/", views.get_processor_schema, name="get_processor_schema"),
    # Processor-specific custom endpoints (dynamic options, validation, defaults, metadata)
    path("v1/processors/<str:processor_name>/options/", views.get_processor_options, name="get_processor_options"),
    path(
        "v1/processors/<str:processor_name>/validate/",
        views.validate_processor_parameters,
        name="validate_processor_parameters",
    ),
    path("v1/processors/<str:processor_name>/defaults/", views.get_processor_defaults, name="get_processor_defaults"),
    path("v1/processors/<str:processor_name>/metadata/", views.get_processor_metadata, name="get_processor_metadata"),
    path(
        "v1/processors/<str:processor_name>/validate-session/",
        views.validate_processor_session,
        name="validate_processor_session",
    ),
    # Copick-specific endpoints
    path("v1/processors/copick/runs/", views.get_copick_runs, name="get_copick_runs"),
    path(
        "v1/processors/copick/annotated-count/",
        views.get_copick_annotated_count,
        name="get_copick_annotated_count",
    ),
    path("v1/processors/copick/template_maps/", views.get_copick_template_maps, name="get_copick_template_maps"),
    # Plan runs endpoint (shared by all processors for run number lookup)
    path("v1/execution/plan_runs/", views.get_plan_runs, name="get_plan_runs"),
    path("v1/execution/execute/", views.execute_pipe, name="execute_pipe"),
    path("v1/execution/preview/", views.preview_script, name="preview_script"),
    path("v1/execution/<int:execution_id>/status/", views.get_execution_status, name="get_execution_status"),
    path("v1/execution/run/<int:proc_run_id>/", views.list_run_executions, name="list_run_executions"),
    path("v1/execution/check_dependencies/", views.check_dependencies, name="check_dependencies"),
    path("v1/execution/lookup_ids/", views.lookup_execution_ids, name="lookup_execution_ids"),
    path("v1/execution/by_job_id/<str:job_id>/", views.get_execution_by_job_id, name="get_execution_by_job_id"),
]
