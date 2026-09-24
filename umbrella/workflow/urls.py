from django.urls import path

from . import views

app_name = "workflow"

urlpatterns = [
    # ============================================================================
    # LEGACY ENDPOINTS (see workflow/legacy/)
    # These use old patterns: Django templates and agent-based job submission
    # For modern API-only patterns, see "MODERN API ENDPOINTS" section below
    # ============================================================================
    # Legacy template-based pages (server-side rendering)
    path("", views.custom_workflow_page, name="custom_workflow"),
    # TODO(legacy-removal): `cancel`/`track` pages superseded by the Next.js jobs
    # UI; remove with their views in workflow/legacy/views/template_views.py.
    path("cancel", views.custom_workflow_cancel, name="cancle workflow jobs"),
    path("track", views.custom_workflow_track, name="track workflow jobs"),
    path("logs", views.custom_workflow_logs, name="job logs"),
    # Legacy dashboard (template + API hybrid)
    path("dashboard/", views.dashboard, name="dashboard"),
    path("data/", views.workflow_get_data, name="dashboard_data"),
    # Legacy job submission (old agent-based pattern)
    path("get_aretomo3", views.get_aretomo3_json, name="json_aretomo3"),
    # LEGACY TEMPLATE-BASED LAUNCH PAGES - FULLY DEPRECATED AND COMMENTED OUT
    # These Django template views have been replaced by the new React-based interface at /processing/pipelines
    # Commented out but kept for reference. Can be removed in a future cleanup.
    # path("run", views.custom_run_workflow_page, name='custom_run_workflow_page'),  # AreTomo3
    # path("denoiset_run", views.cutom_run_denoise_workflow_page, name="custom_denoise_workflow"),
    # path("copick_run", views.cutom_run_create_and_import_copick_page, name="custom_copick_workflow"),
    # path("membraneseg_run", views.custom_run_membraneseg_page, name="custom_membraneseg_workflow"),
    # path("octopi_run", views.custom_run_octopi_page, name="custom_octopi_workflow"),
    # LEGACY JOB SUBMISSION ENDPOINTS - DEPRECATED
    # These endpoints were used by the old template-based forms.
    # New job submissions use /workflow/v1/execution/execute/ via /processing/pipelines
    # path("run_aretomo3", views.run_aretomo3, name='run_aretomo3'),
    # path("run_advanced_aretomo3", views.run_aretomo3_advanced, name='run_advanced_aretomo3'),
    # path("run_denoiset", views.run_denoiset, name='run denoiset'),
    # path("run-create-copick/", views.run_create_copick, name="run_create_copick"),
    # path("run-import-tomogram-copick/", views.run_import_tomogram_copick, name="run_import_tomogram_copick"),
    # path("run-copick-add-object/", views.run_copick_add_object, name="run_add_object_copick"),
    # Legacy utility endpoints (used by dashboard and legacy pages)
    # TODO(legacy-removal): the next three back legacy template pages only (not the
    # Next.js app); remove with cancel_jobs/track_jobs/user_info in
    # workflow/views/job_views.py. See TODO there. (job_logs below is NOT legacy.)
    path("cancel_jobs", views.cancel_jobs, name="cancel_jobs"),
    path("track_jobs", views.track_jobs, name="track_jobs"),
    path("user_info", views.user_info, name="user_details"),
    path("get_msi_session_list", views.get_msi_session_list, name="get all msi session name"),
    path("aretomo3_params", views.get_msi_params_list, name="get parameters"),
    path("denoise_params", views.get_msi_params_list, name="get denoise parameters"),
    path("octopi_params", views.get_msi_params_list, name="get octopi parameters"),
    path("job_logs", views.get_job_logs, name="fetching logs"),
    path("get_plan_id", views.get_plan_id, name="get_plan_id"),
    path("get_msisession_id", views.get_msisession_id, name="get_msisession_id"),
    path("trigger_syncer/", views.trigger_syncer, name="trigger_syncer"),
    path("template_maps/", views.get_template_map_json, name="template_maps"),
    path("status/", views.status_check_api, name="workflow status"),
    # ============================================================================
    # MODERN API ENDPOINTS (for Next.js frontend)
    # These follow API-only patterns and should be used for new development
    # ============================================================================
    # Job Management API (modern)
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
    path(
        "v1/processors/copick/run-objects/",
        views.get_copick_run_objects,
        name="get_copick_run_objects",
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
