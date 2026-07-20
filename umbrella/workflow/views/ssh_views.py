"""
SSH key setup and verification views.

These views handle one-time SSH key setup for users to enable
passwordless authentication from the service user to user accounts
on the compute clusters.
"""

import base64
import json

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from umbrella_logger import logger

from common import clusterio


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Check SSH setup status",
    description="Check if SSH setup is required for the user on the specified cluster",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "string", "description": "Cluster ID (czii or bruno)"},
                "username": {"type": "string", "description": "Username to check (defaults to current user)"},
            },
            "required": ["cluster_id"],
        },
    },
    responses={
        200: OpenApiResponse(description="SSH setup status"),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Server error"),
    },
)
def check_ssh_setup(request):
    """
    Check if SSH setup is required for the user on the specified cluster.

    Resolves the user's cluster username from UserClusterCredentials. If no
    row exists, setup is required and the response username is null so the
    SSH setup modal opens with an empty field. If a row exists, the
    response includes the persisted username for modal pre-fill, and we
    test the actual SSH connection to detect cases where the credentials
    row exists but the service-user key was removed from authorized_keys.
    """
    from accounts.cluster_usernames import MissingClusterCredentialsError, resolve_cluster_username

    try:
        cluster_id = request.data.get("cluster_id")
        explicit_username = request.data.get("username")

        if not cluster_id:
            return JsonResponse({"error": "cluster_id is required"}, status=400)

        if cluster_id not in ["czii", "bruno"]:
            return JsonResponse({"error": 'cluster_id must be "czii" or "bruno"'}, status=400)

        if explicit_username:
            username = explicit_username
        else:
            try:
                username = resolve_cluster_username(request.user, cluster_id)
            except MissingClusterCredentialsError:
                return JsonResponse(
                    {
                        "setup_required": True,
                        "cluster_id": cluster_id,
                        "username": None,
                        "error": None,
                    },
                )

        result = clusterio.test_ssh_as_user(username, cluster_id)

        return JsonResponse(
            {
                "setup_required": not result["can_connect"],
                "cluster_id": result["cluster_id"],
                "username": result["username"],
                "error": result.get("error"),
            },
        )

    except clusterio.SSHDisabledError:
        # No cluster access (e.g. demo server) — don't prompt for SSH setup.
        return JsonResponse(
            {
                "setup_required": False,
                "cluster_id": request.data.get("cluster_id"),
                "username": None,
                "error": None,
                "ssh_disabled": True,
            },
        )
    except Exception as e:
        logger.exception(f"Error in check_ssh_setup: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Setup SSH key for user",
    description="Add service user's SSH public key to user's authorized_keys on the specified cluster",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "string", "description": "Cluster ID (czii or bruno)"},
                "username": {"type": "string", "description": "Username to setup SSH for"},
                "password": {"type": "string", "description": "User password (base64 encoded)"},
            },
            "required": ["cluster_id", "username", "password"],
        },
    },
    responses={
        200: OpenApiResponse(
            description="SSH setup result",
            response={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "can_connect": {"type": "boolean"},
                    "error": {"type": "string", "nullable": True},
                },
            },
        ),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Server error"),
    },
)
def setup_ssh_key(request):
    """
    Setup SSH key access for a user on the specified cluster.

    This endpoint:
    1. Decodes the user's password from base64
    2. Connects to the cluster using the password
    3. Adds the service user's public key to ~/.ssh/authorized_keys
    4. Sets proper permissions
    5. Tests the connection to verify setup
    """
    try:
        data = request.data

        cluster_id = data.get("cluster_id")
        username = data.get("username")
        encoded_password = data.get("password")

        if not all([cluster_id, username, encoded_password]):
            return JsonResponse({"error": "cluster_id, username, and password are required"}, status=400)

        if cluster_id not in ["czii", "bruno"]:
            return JsonResponse({"error": 'cluster_id must be "czii" or "bruno"'}, status=400)

        # Decode password
        try:
            password = base64.b64decode(encoded_password).decode("utf-8")
        except Exception as e:
            return JsonResponse({"error": f"Failed to decode password: {str(e)}"}, status=400)

        # Setup SSH key
        result = clusterio.setup_ssh_key_for_user(username, password, cluster_id)

        # Persist the user's cluster username on success so future SSH
        # connections look up this row instead of guessing from the email.
        if result["success"] and result["can_connect"]:
            from accounts.models import UserClusterCredentials
            from stores.models import Cluster

            cluster = Cluster.objects.get(cluster_id=cluster_id)
            UserClusterCredentials.objects.update_or_create(
                user=request.user,
                cluster=cluster,
                defaults={"username": username},
            )

        return JsonResponse(
            {
                "success": result["success"],
                "message": result["message"],
                "can_connect": result["can_connect"],
                "error": result.get("error"),
            },
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        logger.exception(f"Error in setup_ssh_key: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
