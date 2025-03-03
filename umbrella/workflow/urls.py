from django.urls import path
from . import views

app_name = "workflow"

urlpatterns = [
    path("get_aretomo3", views.get_aretomo3_json, name='json_aretomo3'),
    path("run", views.custom_run_workflow_page, name='custom_run_workflow_page'),
    path("", views.custom_workflow_page, name='custom_workflow'),
    path("denoiset_run", views.cutom_run_denoise_workflow_page, name="custom_denoise_workflow"),
    path("cancel", views.custom_workflow_cancel, name='cancle workflow jobs'),
    path("track", views.custom_workflow_track, name='track workflow jobs'),
    path("run_aretomo3", views.run_aretomo3, name='run_aretomo3'),
    path("cancel_jobs", views.cancel_jobs, name='cancel_jobs'),
    path("track_jobs", views.track_jobs, name='track_jobs'),
    path("user_info", views.user_info, name='user_details'),
    path("get_msisession_list", views.get_msi_session_list, name='get all msi session name'),
    path("run_advanced_aretomo3", views.run_aretomo3_advanced, name='run_advanced_aretomo3'),
    path("run_denoiset", views.run_denoiset, name='run denoiset'),
    path("aretomo3_params", views.get_msi_params_list, name='get parameters'),
    path("job_logs", views.get_job_logs, name='fetching logs'),
    path("dashboard/", views.dashboard, name='dashboard'),
    path('data/', views.workflow_get_data, name='dashboard_data'),
]