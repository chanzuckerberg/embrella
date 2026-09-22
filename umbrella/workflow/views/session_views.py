"""
Session lookup views.

Small JSON endpoints the Next.js app still calls by their pre-v1 paths:
`/workflow/get_aretomo3`, `/workflow/get_msi_session_list`, `/workflow/get_msisession_id`.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.services.cluster_resolver import cluster_id_for_run
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from stores.models import Cluster, resolve_review_path
from tem.models import MsiSession
from umbrella_logger import logger

from common import clusterio
from common.clusterio import jsonify
from common.httpio import fetch_remote_text
from common.sorting import msi_session_sort_key
from workflow.views.constants import KEYS

ARETOMO3_SESSION_JSON = "AreTomo3_Session.json"
RUN_PREFIX = "run"


@extend_schema(
    methods=["GET"],
    description="Fetches parsed Aretomo3 JSON metadata for a given session and run ID.",
    parameters=[
        OpenApiParameter(
            name="session", required=True, type=OpenApiTypes.STR, description="Session name (e.g. 23sep23a)"
        ),
        OpenApiParameter(name="run_id", required=True, type=OpenApiTypes.STR, description="Run ID (e.g. 001)"),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@login_required
def get_aretomo3_json(request):
    """Fetch and parse AreTomo3 session JSON metadata."""
    session_name = request.GET.get("session")
    run_id = request.GET.get("run_id")

    if not session_name or not run_id:
        error_msg = "Session name and run ID are required."
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=400)

    # ProcRun.name is e.g. "run003"; the frontend passes just "003".
    run_name = run_id if run_id.startswith(RUN_PREFIX) else f"{RUN_PREFIX}{run_id}"

    cluster_id = request.GET.get("cluster_id") or cluster_id_for_run(session_name, run_name)

    try:
        cluster = Cluster.objects.get(cluster_id=cluster_id, is_active=True)
    except Cluster.DoesNotExist:
        return JsonResponse({"error": f"Unknown cluster_id: {cluster_id}"}, status=400)

    try:
        msi_session = MsiSession.objects.get(name=session_name)
    except MsiSession.DoesNotExist:
        return JsonResponse({"error": f"Session not found: {session_name}"}, status=404)

    base_proc_url = resolve_review_path(
        "proc_url",
        cluster,
        msi_session=msi_session,
        proc_software="aretomo3",
        proc_run=run_name,
        backend_fetch=True,
    )
    session_json_url = f"{base_proc_url}{ARETOMO3_SESSION_JSON}"

    try:
        # Fetch the session JSON over HTTP from the Caddy file server (no SSH needed).
        full_data = jsonify(fetch_remote_text(session_json_url))

        version = full_data["software"]["version"]
        gain = full_data["input"]["Gain"]
        parsed_data = clusterio.extract_parameters(full_data, KEYS)

        # Version and gain lead the table.
        return JsonResponse({"Version": version, "Gain": gain, **parsed_data}, safe=False)
    except FileNotFoundError:
        error_msg = "File not found"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=404)
    except Exception as err:
        error_msg = f"Please check the server status: {str(err)}"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns a list of all MSI session names.",
    responses={
        200: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_msi_session_list(request):
    """All MSI session names, newest first."""
    try:
        session_names = list(MsiSession.objects.values_list("name", flat=True))
        return JsonResponse({"session_names": sorted(session_names, key=msi_session_sort_key)}, status=200)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@csrf_exempt
def get_msisession_id(request):
    """Get MsiSession ID by session name."""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    session_name = request.GET.get("session_name")
    if not session_name:
        return JsonResponse({"error": "Session name not provided"}, status=400)

    try:
        session = MsiSession.objects.get(name=session_name)
        return JsonResponse({"session_id": session.id})
    except MsiSession.DoesNotExist:
        return JsonResponse({"error": f"Session {session_name} not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
