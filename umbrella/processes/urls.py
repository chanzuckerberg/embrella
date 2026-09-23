from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import StorageDecisionViewSet, StorageSessionViewSet

# register app namespace
app_name = "processes"

router = DefaultRouter()
router.register(r"v1/storage-sessions", StorageSessionViewSet, basename="storage-sessions")
router.register(r"v1/storage-decisions", StorageDecisionViewSet, basename="storage-decisions")

# JSON API routes, included under /processes/.
v1_urlpatterns = [
    path("v1/filterlist/", views.available_filters, name="get_processes_details"),
    path("v1/tomograms/", views.get_tomo_details, name="get proc run details"),
    path("v1/annotations/", views.get_annotation_details, name="annotation details"),
    # Filesystem Survey and Directory endpoints
    path("v1/surveys/", views.get_surveys, name="get_surveys"),
    path("v1/surveys/<int:survey_id>/files/", views.get_survey_files, name="get_survey_files"),
    path("v1/directories/", views.get_directories, name="get_directories"),
    path("v1/directories/stats/", views.get_directory_stats, name="get_directory_stats"),
    path("v1/directories/filterlist/", views.get_directory_filterlist, name="get_directory_filterlist"),
    path("v1/directories/bulk_update_status/", views.bulk_update_directory_status, name="bulk_update_directory_status"),
    path("v1/directories/<int:directory_id>/files/", views.get_directory_files, name="get_directory_files"),
] + router.urls

urlpatterns = v1_urlpatterns
