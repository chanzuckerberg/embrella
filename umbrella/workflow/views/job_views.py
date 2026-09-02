"""
Job management views.

These views handle job tracking, cancellation, and log retrieval
for SLURM jobs running on compute clusters.

TODO(legacy-removal): `user_info`, `cancel_jobs`, and `track_jobs` in this module
are legacy — they are only used by the old Django template pages served under
/workflow (`custom_workflow_cancel` -> workflows/workflow_cancel.html, and
`custom_workflow_track` -> workflows/workflow_track.html in
workflow/legacy/views/template_views.py). The Next.js app does NOT call them; it
uses the newer job_api.py endpoints instead (/workflow/v1/jobs/,
/workflow/v1/jobs/bulk_cancel/, ...). When the legacy template pages are retired,
remove these three views + their url routes (workflow/urls.py: track_jobs,
cancel_jobs, user_info, and the `track`/`cancel` template routes) + the two
templates. NOTE: `get_job_logs` is NOT legacy — it backs the Next.js
JobLogsModal (JOB_LOGS = /workflow/job_logs/) and must stay.
"""

import base64

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import JobLog, PipeExecution
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from umbrella_logger import logger

from common import clusterio

from ..agent import RemoteJobSubmitter, StatusChecker
from .utils import format_job_output


def user_info(request):
    """Get current user information."""
    username = request.user.username.split("@")[0]
    response_data = {"username": username}
    return JsonResponse(response_data, safe=False, status=200)


@extend_schema(
    methods=["POST"],
    description="Cancels a submitted SLURM job on the remote server.",
    request={
        "type": "object",
        "properties": {
            "job_number": {"type": "string", "description": "The job ID to cancel"},
            "user_id": {"type": "string", "description": "Remote login user ID"},
            "password": {"type": "string", "description": "Base64-encoded remote password"},
        },
        "required": ["job_number"],
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@login_required
def cancel_jobs(request):
    """Cancel a SLURM job by job number."""
    if request.method == "POST":
        data = request.data  # json.loads(request.body)
        job_number = data.get("job_number")

        # Retrieve user_id and decoded_password from session
        user_id = request.session.get("user_id")
        decoded_password = request.session.get("decoded_password")

        if user_id is None and decoded_password is None:
            user_id = data.get("user_id")
            encoded_password = data.get("password")
            decoded_password = base64.b64decode(encoded_password).decode("utf-8")

        canceler = RemoteJobSubmitter(
            cluster_id="czii",
            auth={"username": user_id, "password": decoded_password},
            remote_script_dir=None,
        )
        try:
            # Connect to the remote server
            canceler.connect()

            output, error = canceler.cancel(job_number)

            # Update PipeExecution record with correct timestamp
            pipe_exec = PipeExecution.objects.filter(job_id=job_number).first()
            if pipe_exec:
                pipe_exec.status = "cancelled"
                pipe_exec.completed_at = dj_timezone.now()
                pipe_exec.save(update_fields=["status", "completed_at"])
                logger.info(f"Updated PipeExecution for cancelled job {job_number}")

            return JsonResponse({"message": f"Job - {job_number} for canceled successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            canceler.close()

    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def track_jobs(request):
    """
    Handle a GET request to track jobs. If 'job_name' is specified in
    the query parameters, track only that job. Otherwise, track all jobs.
    """
    if request.method == "GET":
        job_name = request.GET.get("job_name")  # None if not provided

        try:
            checker = StatusChecker(
                cluster_id="czii",
                auth=clusterio.get_auth_service_user(),
            )
        except clusterio.SSHDisabledError:
            # No cluster access (e.g. demo server) — degrade to an empty job list.
            return JsonResponse({"jobs": []})

        try:
            # Connect to the remote server
            checker.connect()

            if job_name is None:
                output, error = checker.track_jobs(job_name=None, all=True)
            else:
                output, error = checker.track_jobs(job_name)

            formatted_output = format_job_output(output)
            return JsonResponse({"jobs": formatted_output})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            checker.close()

    # If the request is not GET, return an error
    return JsonResponse({"error": "Invalid request method"}, status=400)


@extend_schema(
    methods=["GET"],
    description="Returns job logs for all users or filters by a specific username if provided.",
    parameters=[
        OpenApiParameter(
            name="user_name",
            required=False,
            type=OpenApiTypes.STR,
            description="Filter logs by user name",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_job_logs(request):
    """Fetch job logs with optional user filtering."""
    try:
        # Extract user_name from query parameters
        user_name = request.GET.get("user_name", None)

        # Fetch all JobLog entries
        job_logs = JobLog.objects.all().values(
            "user",
            "job_name",
            "advanced",
            "job_id",
            "created_at",
            "parameters",
            "error_message",
        )

        job_logs_list = list(job_logs)

        # Flip 'user' -> 'user_id' and 'parameters.user_id' -> 'parameters.user'
        filtered_job_logs = []
        for entry in job_logs_list:
            # 1) Rename top-level 'user' to 'user_id'
            entry["user_id"] = entry.pop("user", None)

            # 2) Inside 'parameters', rename 'user_id' to 'user'
            params = entry.get("parameters", {})
            if "user_id" in params:
                params["user"] = params.pop("user_id")

            # Update the entry's parameters
            entry["parameters"] = params

            # 3) Filter by user_name if provided
            if user_name is None or (params.get("user") == user_name):
                filtered_job_logs.append(entry)

        return JsonResponse({"job_logs": filtered_job_logs}, status=200)

    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching job logs: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
