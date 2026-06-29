"""URLconf for the people directory API (included under /people/)."""

from rest_framework.routers import DefaultRouter

from people.viewsets import (
    InstitutionViewSet,
    PersonViewSet,
)

router = DefaultRouter()
router.register(r"v1/people", PersonViewSet, basename="person")
router.register(r"v1/institutions", InstitutionViewSet, basename="institution")

urlpatterns = router.urls
