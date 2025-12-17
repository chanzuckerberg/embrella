from django.urls import path
from rest_framework.routers import DefaultRouter

from external_links.views import ExternalResourceViewSet

# Create a router for the viewset
router = DefaultRouter()
router.register(r'', ExternalResourceViewSet, basename='external-resource')

urlpatterns = router.urls
