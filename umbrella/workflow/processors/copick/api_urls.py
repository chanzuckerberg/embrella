"""Top-level URLconf for copick viewer-facing API (/copick/v1/)."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "v1/projects/",
        views.list_copick_projects,
        name="copick_list_projects",
    ),
    path(
        "v1/projects/<str:session_name>/<str:run_name>/",
        views.get_copick_project_detail,
        name="copick_project_detail",
    ),
    path(
        "v1/projects/<str:session_name>/<str:run_name>/scan/",
        views.trigger_copick_scan,
        name="copick_trigger_scan",
    ),
]
