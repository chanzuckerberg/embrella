"""
Session-related view functions for processing workflows.

This module contains views for querying MSI session information.
"""

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from tem.models import MsiSession

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns the ID of a session given a session name (query param: name).",
    parameters=[
        OpenApiParameter(name="name", required=True, type=str, description="Name of the MSI session"),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_session_id(request):
    """
    API endpoint to get MSI session ID by session name.
    URL: /processes/api/get-session-id?name=SESSION_NAME
    """
    try:
        session_name = request.GET.get("name")
        if not session_name:
            return JsonResponse({"error": "Session name parameter is required"}, status=400)

        # Query the MsiSession model to find a session with the provided name
        session = MsiSession.objects.filter(name=session_name).first()

        if not session:
            return JsonResponse({"error": f"No session found with name: {session_name}"}, status=404)

        # Return the session ID
        return JsonResponse({"id": session.id, "name": session.name})

    except Exception as e:
        logger.error(f"Error getting session ID: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
