"""
Job log views.

Backs the Next.js JobLogsModal (`/workflow/job_logs/`).
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import JobLog
from rest_framework.decorators import api_view
from umbrella_logger import logger


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
