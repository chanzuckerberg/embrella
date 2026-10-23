from rest_framework.routers import DefaultRouter

from .viewsets import ImageViewSet

app_name = "images"

router = DefaultRouter()
router.register(r"v1/images", ImageViewSet, basename="image")

urlpatterns = router.urls
