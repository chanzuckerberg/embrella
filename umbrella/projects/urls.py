from rest_framework.routers import DefaultRouter

from .viewsets import ProjectViewSet

# register app namespace
app_name = "projects"

router = DefaultRouter()
router.register(r"v1/projects", ProjectViewSet, basename="project")

urlpatterns = router.urls
