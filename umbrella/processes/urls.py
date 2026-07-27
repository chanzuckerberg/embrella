from django.urls import path

from . import views

# register app namespace
app_name = "processes"

urlpatterns = [
    path("reserve", views.reserve_run, name="reserve"),
    path("create", views.create_run, name="create"),
    path("<int:run_id>/", views.detail, name="detail"),
    path("post_tomo/reserve", views.reserve_run_post_tomo, name="ptreserve"),
    path("post_tomo/create", views.create_run_post_tomo, name="ptcreate"),
    path("post_tomo/<int:run_id>/", views.detail_post_tomo, name="ptdetail"),
    path("v1/filterlist/", views.available_filters, name="get_processes_details"),
    path("v1/tomograms/", views.get_tomo_details, name="get proc run details"),
    path("v1/annotations/", views.get_annotation_details, name="annotation details"),
    path("api/get-session-id", views.get_session_id, name="get_session_id"),
    # path('detail_params',views.detail_params, name='abc')
    # path("run_list/", views.get_all_sessions, name="get"),
    # path("path_list/", views.get_all_image_paths, name="path")
    path("sync_tomograms/", views.sync_tomograms_view, name="sync_tomograms"),
    path("get_runs/", views.get_runs, name="get_runs"),
    path("get_tomogram_stats/", views.get_tomogram_stats, name="get_tomogram_stats"),
    path("start_sync/", views.start_sync, name="start_sync"),
    path("post_generic/reserve", views.reserve_generic_run, name="pg_reserve"),
    path("post_generic/create", views.create_generic_run, name="pg_create"),
    # Filesystem Survey and Directory endpoints
    path("v1/surveys/", views.get_surveys, name="get_surveys"),
    path("v1/surveys/<int:survey_id>/files/", views.get_survey_files, name="get_survey_files"),
    path("v1/directories/", views.get_directories, name="get_directories"),
    path("v1/directories/stats/", views.get_directory_stats, name="get_directory_stats"),
    path("v1/directories/filterlist/", views.get_directory_filterlist, name="get_directory_filterlist"),
    path("v1/directories/bulk_update_status/", views.bulk_update_directory_status, name="bulk_update_directory_status"),
    path("v1/directories/<int:directory_id>/files/", views.get_directory_files, name="get_directory_files"),
]
