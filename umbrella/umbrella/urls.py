"""
URL configuration for umbrella project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# Import API views from their respective app-level modules
from cryo_grids.api.views import (
    get_available_grids,
    get_grids_by_cassette,
    get_grids_by_user,
)
from cryo_grids.viewsets import (
    CaneViewSet,
    CryoGridViewSet,
    FreezingSessionViewSet,
    GridLoggingChoicesViewSet,
    LabelViewSet,
    ProjectLeaderViewSet,
    PuckViewSet,
    SampleViewSet,
    SpecimenViewSet,
)
from custom.views import version_info
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from processes.api.views import (
    ReviewTomogramView,
    ReviewView,
    export_review_results,
    get_review_tomograms,
    get_tomo_by_msi_session,
)
from processes.views import available_annotation_filter
from rest_framework.routers import DefaultRouter
from tem.api.views import SessionView
from tem.urls import legacy_urlpatterns as tem_legacy_urlpatterns
from tem.urls import v1_urlpatterns as tem_v1_urlpatterns

from umbrella.ping import ping
from umbrella.user import get_user_info
from umbrella.views import custom_google_sso_callback, custom_login_view, custom_logout_view
from umbrella.viewsets import UserViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"api/list/all/users", UserViewSet, basename="user")
router.register(r"api/list/pucks", PuckViewSet, basename="puck")
router.register(r"api/grid-logging/choices", GridLoggingChoicesViewSet, basename="grid-logging-choices")

# Grid Logging ViewSets
router.register(r"api/list/canes", CaneViewSet, basename="cane")
router.register(r"api/list/specimens", SpecimenViewSet, basename="specimen")
router.register(r"api/list/samples", SampleViewSet, basename="sample")
router.register(r"api/list/freezing-sessions", FreezingSessionViewSet, basename="freezing-session")
router.register(r"api/list/grids", CryoGridViewSet, basename="grid")
router.register(r"api/list/project-leaders", ProjectLeaderViewSet, basename="project-leader")
router.register(r"api/list/labels", LabelViewSet, basename="label")

import mimetypes

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.static import serve


@login_required
def documentation_view(request, path):
    if path == "":
        path = "index.html"
    elif path[-1] == "/":
        path = f"{path}index.html"
    # if not settings.DOCUMENTATION_ACCESS_FUNCTION(request.user):
    #    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    if not settings.DOCUMENTATION_XSENDFILE:
        return serve(request, path, settings.DOCUMENTATION_HTML_ROOT)
    mimetype, encoding = mimetypes.guess_type(path)
    response = HttpResponse(content_type=mimetype)
    response["Content-Encoding"] = encoding
    response["Content-Disposition"] = ""
    response["X-Sendfile"] = "".join([settings.DOCUMENTATION_HTML_ROOT, path])
    return response


# sURLs =[static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
#         static("/docs/", document_root=settings.STATIC_ROOT),]
# API-only endpoints (no template rendering)
api_patterns = [
    # API endpoints for data
    path("api/sessions/", SessionView.as_view(), name="session-list"),
    path("api/sessions/<str:session_id>/", SessionView.as_view(), name="session-detail"),
    path("api/reviews/", ReviewView.as_view(), name="reviews"),
    path("api/reviews/<str:review_id>/", ReviewView.as_view(), name="review_metadata"),
    path("api/reviews/<str:review_id>/save", ReviewView.as_view(), name="save_review"),
    path("api/reviews/<str:review_id>/complete", ReviewView.as_view(), name="complete_review"),
    path("api/reviews/<str:review_id>/export", export_review_results, name="export_review_results"),
    path("api/reviews/<str:review_id>/tomograms", get_review_tomograms, name="get_review_tomograms"),
    path(
        "api/reviews/<str:review_id>/tomograms/<str:tomogram_id>",
        ReviewTomogramView.as_view(),
        name="review_tomogram_detail_no_slash",
    ),
    # API schema and docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redocs/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Other API endpoints
    path("user", get_user_info, name="user_info"),
    path("ping/", ping),
    path("version", version_info, name="version_info"),
    path("get_grids_by_user/", get_grids_by_user, name="get_grids_by_user"),
    path("get_grids_by_cassette/", get_grids_by_cassette, name="get_grids_by_cassette"),
    path("get_tomo_by_msi_session/", get_tomo_by_msi_session, name="get_tomo_by_msi_session"),
    path("available_grids", get_available_grids, name="get_available_grids"),
    path("annotations/v1/filterlist/", available_annotation_filter, name="get filter list for annotations"),
    # External resources (documentation links)
    path("api/external-resources/", include("external_links.urls")),
]

# Legacy template-based routes (will be migrated to Next.js)
legacy_patterns = [
    path("umbrella/", include("custom.urls"), name="umbrella"),
    path("projects/", include("projects.urls")),
    path("tem/", include((tem_legacy_urlpatterns, "tem"))),
    path("processes/", include("processes.urls")),
    path("cryo_grids/", include("cryo_grids.urls"), name="cryo_grids"),
    path("workflow/", include("workflow.urls"), name="workflow pipeline"),
]

urlpatterns = (
    [
        # Root redirect to legacy umbrella (for direct Django access)
        # In production, nginx routes root (/) to Next.js frontend
        path("", RedirectView.as_view(url="/legacy/umbrella/", permanent=False)),
        # Django admin and authentication
        # Note: Specific paths must come BEFORE the admin catchall
        path("admin/login/", custom_login_view, name="login"),
        path("admin/logout/", custom_logout_view, name="logout"),
        path("admin/", admin.site.urls, name="admin"),
        # Override Google SSO callback to preserve full frontend URL
        path("google_sso/callback/", custom_google_sso_callback, name="custom_google_sso_callback"),
        path("google_sso/", include("django_google_sso.urls", namespace="django_google_sso")),
        # Documentation
        re_path(r"^docs/(?P<path>.*)$", documentation_view, name="docs"),
        # Legacy template-based views (all under /legacy/ prefix)
        path("legacy/", include(legacy_patterns)),
        # API routes for Next.js frontend (these apps have v1/ API endpoints)
        # Note: These also include legacy template routes which should eventually move to /legacy/
        path("workflow/", include("workflow.urls"), name="workflow"),
        path("cryo_grids/", include("cryo_grids.urls"), name="cryo_grids"),
        path("processes/", include("processes.urls"), name="processes"),
        path("projects/", include("projects.urls"), name="projects"),
        path("tem/", include(tem_v1_urlpatterns)),
    ]
    + api_patterns  # API endpoints
)


# Include router URLs
urlpatterns += router.urls

# change header name
admin.site.site_header = "Embrella"
admin.site.site_title = "Embrella"
admin.site.site_url = "/legacy/umbrella"
