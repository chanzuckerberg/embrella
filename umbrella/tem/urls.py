from django.urls import path
from rest_framework.routers import SimpleRouter

from .api import v1_views
from .viewsets import MsiSessionOverviewViewSet

# register app namespace
app_name = "tem"

v1_router = SimpleRouter()
v1_router.register(r"v1/session-overview", MsiSessionOverviewViewSet, basename="session-overview")

# v1 API endpoints (included under /tem/)
v1_urlpatterns = [
    path("v1/sessions/", v1_views.sessions, name="v1_sessions"),
    path("v1/sessions/form-options/", v1_views.form_options, name="v1_form_options"),
    path("v1/sessions/suggest-name/", v1_views.suggest_session_name, name="v1_suggest_name"),
    path("v1/sessions/<str:name>/", v1_views.session_detail, name="v1_session_detail"),
    path("v1/magnifications/", v1_views.get_magnifications, name="v1_magnifications"),
    *v1_router.urls,
]
