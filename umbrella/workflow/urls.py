from django.urls import path
from . import views

app_name = "workflow"

urlpatterns = [
    path("get_aretomo3", views.get_aretomo3_json, name='json_aretomo3'),
    path("run", views.custom_run_workflow_page, name='custom_run_workflow_page'),
    path("", views.custom_workflow_page, name='custom_workflow'),
    path("run_aretomo3", views.run_aretomo3, name='run_aretomo3'),
    path("cancel_aretomo3", views.cancel_aretomo3, name='cancel_aretomo3'),
    path("track_jobs", views.track_jobs, name='track_jobs'),
    path("user_info", views.user_info, name='user_details'),
    path("get_msisession_list", views.get_msi_session_list, name='get all msi session name')
]