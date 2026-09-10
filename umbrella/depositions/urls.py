"""URLconf for the depositions (mounted at /depositions/)."""

from rest_framework.routers import DefaultRouter

from .views import (
    DatasetViewSet,
    DepositionSessionViewSet,
    DepositionViewSet,
)

router = DefaultRouter()
router.register(r"v1/depositions", DepositionViewSet, basename="deposition")
router.register(r"v1/datasets", DatasetViewSet, basename="deposition-dataset")
router.register(r"v1/sessions", DepositionSessionViewSet, basename="deposition-session")

urlpatterns = router.urls
