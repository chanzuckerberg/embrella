from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import ProjectViewSet

# register app namespace
app_name = "projects"

router = DefaultRouter()
router.register(r"v1/projects", ProjectViewSet, basename="project")

urlpatterns = [
    path("project_list/", views.getproject, name="projects list"),
    path("create_project/", views.create_project, name="create project"),
] + router.urls
