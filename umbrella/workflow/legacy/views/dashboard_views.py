"""
Dashboard and session management views.

These views handle workflow dashboard display, MSI session listing,
and related data fetching for workflow management UI.
"""

import json
import os
import subprocess
from pathlib import Path

from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import ProcPlan, ProcRun
from rest_framework.decorators import api_view
from tem.models import MsiSession
from umbrella_logger import logger

from common import clusterio
from workflow.agent import StatusChecker
from workflow.views.constants import (
    HOST,
    KEYFILE,
    PORT,
    STATUS_CHECKER_SCRIPT_PATH,
    STATUS_CHECKER_TEMPLATE_PATH,
    USERNAME,
)
from workflow.views.utils import format_job_output, parse_script_output


def dashboard(request):
    """
    Render the dashboard page with the dynamic graph.
    """
    return render(request, "workflows/workflow_dashboard.html")


@csrf_exempt
def workflow_get_data(request):
    """
    Fetch all job data directly from the internal track_jobs functionality.
    Process it by counting jobs either per job name or per user based on
    the 'group_by' request parameter.
    """
    try:
        # Initialize and connect to remote
        checker = StatusChecker(
            cluster_id="czii",
            auth=clusterio.get_auth_service_user(),
            remote_script_dir=None,
            local_template_path=None,
        )
        checker.connect()

        # Since we want all jobs, set job_name=None and all=True
        output, error = checker.track_jobs(job_name=None, all=True)

        # Close the connection in the finally block
        formatted_output = format_job_output(output)
        # `formatted_output` should be a list of job dicts, e.g.:
        # [{'USER': '...', 'NAME': '...'}, ...]

        # Check for a 'group_by' GET parameter, defaulting to 'job' if not provided.
        group_by = request.GET.get("group_by", "job").lower()
        logger.debug(f"group_by parameter: {group_by}")

        # Now we reuse the grouping logic
        if group_by == "user":
            # Group jobs by user -> user_counts[user][job_name] = count
            user_counts = {}
            for job in formatted_output:
                user = job.get("USER", "Unknown")
                job_name = job.get("NAME", "Unknown")
                user_counts.setdefault(user, {})
                user_counts[user][job_name] = user_counts[user].get(job_name, 0) + 1
            result = user_counts
        else:
            # Default: group jobs by job name -> name_counts[job_name] = count
            name_counts = {}
            for job in formatted_output:
                job_name = job.get("NAME", "Unknown")
                name_counts[job_name] = name_counts.get(job_name, 0) + 1
            result = name_counts

    except Exception as e:
        logger.exception("An error occurred while fetching or processing data.")
        result = {"error": str(e)}
    finally:
        # Ensure the connection is closed even if an exception is raised
        try:
            checker.close()
        except Exception:
            pass

    return JsonResponse(result)


@extend_schema(
    methods=["GET"],
    description="Triggers a remote status check for a given session via SSH.",
    parameters=[
        OpenApiParameter(
            name="session_name",
            required=True,
            type=OpenApiTypes.STR,
            description="MSI session name used to run the status-check script",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
@csrf_exempt
def status_check_api(request):
    """
    API endpoint to trigger a remote status check via a GET call.
    Expects a query parameter: ?session_name=your_session_id

    The SSH credentials and configuration are read from environment variables/constants:
      - HOST, PORT, USERNAME, KEYFILE
      - STATUS_CHECKER_SCRIPT_PATH (remote_script_dir)
      - STATUS_CHECKER_TEMPLATE_PATH (local_template_path)
    """
    session_name = request.GET.get("session_name")
    if not session_name:
        return JsonResponse({"error": "Missing 'session_name' parameter."}, status=400)

    try:
        # Load credentials and configuration from environment variables/constants
        remote_script_dir = STATUS_CHECKER_SCRIPT_PATH
        local_template_path = STATUS_CHECKER_TEMPLATE_PATH

        if not all([HOST, PORT, USERNAME, KEYFILE, remote_script_dir, local_template_path]):
            return JsonResponse(
                {"error": "Server configuration incomplete. Please check environment variables."},
                status=500,
            )

        # Instantiate and use the StatusChecker
        checker = StatusChecker(
            cluster_id="czii",
            auth=clusterio.get_auth_service_user(),
            remote_script_dir=remote_script_dir,
            local_template_path=local_template_path,
        )
        checker.connect()
        # live_denoising is set to False by default
        raw_output, script_error = checker.check_status(session_name, live_denoising=False)
        checker.close()

        # Parse the raw output into a structured dictionary
        parsed_output = parse_script_output(raw_output)

        response_data = {"result": parsed_output}
        if script_error.strip():
            response_data["error"] = script_error.strip()

        return JsonResponse(response_data, status=200, json_dumps_params={"indent": 4})

    except Exception as e:
        logger.exception("Error during status check API")
        return JsonResponse({"error": str(e)}, status=500)


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
    """Fetch all MSI session names and return them sorted."""
    try:
        # Fetch session names and sort them
        session_names = list(MsiSession.objects.values_list("name", flat=True))

        # Sort the session names
        def sort_key(name):
            try:
                # Extract components from the name
                year = int(name[:2])
                month = name[2:5].lower()  # Convert to lowercase for consistent comparison
                day = int(name[5:7])
                seq = name[7] if len(name) > 7 else "a"  # Default to 'a' if no sequence letter

                # Convert month to number for proper sorting
                month_map = {
                    "jan": 1,
                    "feb": 2,
                    "mar": 3,
                    "apr": 4,
                    "may": 5,
                    "jun": 6,
                    "jul": 7,
                    "aug": 8,
                    "sep": 9,
                    "oct": 10,
                    "nov": 11,
                    "dec": 12,
                }

                # Check if month is valid
                if month not in month_map:
                    return (0, 0, 0, "z")  # Move invalid months to the end

                month_num = month_map[month]

                # Validate year and day
                if not (0 <= year <= 99) or not (1 <= day <= 31):
                    return (0, 0, 0, "z")  # Move invalid dates to the end

                # Return tuple for sorting (negative year for descending order)
                return (-year, -month_num, -day, seq)
            except (ValueError, IndexError):
                # If name doesn't match expected format, put it at the end
                return (0, 0, 0, "z")

        # Sort the session names using our custom sort key
        sorted_session_names = sorted(session_names, key=sort_key)

        return JsonResponse({"session_names": sorted_session_names}, status=200)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@extend_schema(
    methods=["GET"],
    description="""Returns MSI sessions and associated run numbers for a given processing plan type.

Used to determine the next available run number when submitting jobs.

**Supported plan types:**
- `aretomo3` → czii-live plan (default)
- `denoise` → czii-denoise plan
- `copick` → czii-copick plan (create project)
- `copick-add-object` → copick-add-object plan (add pickable objects)
- `membraneseg` → membraneseg plan (membrane segmentation)
- TODO: `octopi` → czii-octopi plan

**Example response:**
```json
{
  "sessions": [
    {"name": "24nov10", "run_numbers": ["001", "002", "003"]},
    {"name": "24dec05", "run_numbers": ["001"]}
  ]
}
```

Run numbers are returned without the 'run' prefix. To get the next run name,
find the max number and increment (e.g., max "003" → next is "run004").
""",
    parameters=[
        OpenApiParameter(
            name="plan_type",
            required=False,
            type=OpenApiTypes.STR,
            description="Processing plan type. One of: aretomo3, denoise, copick, copick-add-object, octopi. Defaults to 'aretomo3'.",
            enum=["aretomo3", "denoise", "copick", "copick-add-object", "octopi"],
        ),
        OpenApiParameter(
            name="session_name",
            required=False,
            type=OpenApiTypes.STR,
            description="Optional MSI session name to filter results to a single session.",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_msi_params_list(request):
    """Get MSI sessions with their run numbers, optionally filtered by session name."""
    try:
        # Get the msi_session name from request parameters
        session_name_filter = request.GET.get("session_name", None)
        plan_type = request.GET.get("plan_type", "aretomo3")  # Default to aretomo3 for backward compatibility

        # Map plan_type → ProcPlan.name
        plan_map = {
            "aretomo3": "czii-live",
            "denoise": "czii-denoise",
            "copick": "czii-copick",
            "copick-add-object": "copick-add-object",
            "copick-import": "copick-import",
            "membraneseg": "membraneseg",
            "octopi": "czii-octopi",
        }
        if plan_type not in plan_map:
            return JsonResponse({"error": f'Unsupported plan_type "{plan_type}"'}, status=400)

        plan_name = plan_map[plan_type]
        logger.info(f"Plan type: {plan_type}, Plan name: {plan_name}")

        # Get the plan ID
        try:
            plan = ProcPlan.objects.get(name=plan_name)
            plan_id = plan.id
            logger.info(f"Found plan {plan_name} with ID: {plan_id}")
        except ProcPlan.DoesNotExist:
            logger.error(f"Processing plan {plan_name} not found")
            return JsonResponse({"error": f"Processing plan {plan_name} not found"}, status=404)

        # Perform the join between tem_msisession and processes_procrun
        # Let's try a more explicit query to debug the issue
        query = (
            MsiSession.objects.filter(procrun__proc_plan_id=plan_id)  # Filter by processing plan first
            .annotate(
                run_number=F("procrun__name"),  # Map the 'name' field from the procrun table
                run_created_at=F("procrun__created_at"),  # Include the created_at field for sorting
            )
            .values("name", "run_number", "run_created_at")
            .distinct()  # Remove duplicates
        )

        # Apply filtering if a session name is provided
        if session_name_filter:
            query = query.filter(name=session_name_filter)

        # Let's also check what's in the ProcRun table directly for debugging
        direct_procrun_query = ProcRun.objects.filter(proc_plan_id=plan_id)
        if session_name_filter:
            direct_procrun_query = direct_procrun_query.filter(msi_session__name=session_name_filter)

        direct_results = list(direct_procrun_query.values("msi_session__name", "name", "created_at"))
        logger.info(f"Direct ProcRun query returned {len(direct_results)} results for plan_id={plan_id}")
        for entry in direct_results:
            logger.info(f"Direct ProcRun result: {entry}")

        # Execute the query and log the results for debugging
        query_results = list(query)
        logger.info(
            f"Query returned {len(query_results)} results for plan_id={plan_id}, session_name_filter={session_name_filter}",
        )
        for entry in query_results:
            logger.info(f"Query result: {entry}")

        # Group results by name and collect unique run numbers with sorting by created_at
        grouped_sessions = {}
        for entry in query_results:
            name = entry["name"]
            run_number = entry["run_number"]
            created_at = entry["run_created_at"]
            if name not in grouped_sessions:
                grouped_sessions[name] = []
            if run_number:
                # Remove 'run' prefix if it exists
                stripped_run_number = run_number.replace("run", "")
                grouped_sessions[name].append((stripped_run_number, created_at))

        # Sort run numbers by created_at (most recent first) and format the response
        formatted_sessions = [
            {
                "name": name,
                "run_numbers": [run[0] for run in sorted(run_numbers, key=lambda x: x[1], reverse=True)],
            }
            for name, run_numbers in grouped_sessions.items()
        ]

        return JsonResponse({"sessions": formatted_sessions}, status=200)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@csrf_exempt
def get_plan_id(request):
    """Get ProcPlan ID by plan name."""
    if request.method == "GET":
        plan_name = request.GET.get("plan_name")
        if not plan_name:
            return JsonResponse({"error": "Plan name not provided"}, status=400)

        try:
            plan = ProcPlan.objects.get(name=plan_name)
            return JsonResponse({"plan_id": plan.id})
        except ProcPlan.DoesNotExist:
            return JsonResponse({"error": f"Plan {plan_name} not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def get_msisession_id(request):
    """Get MsiSession ID by session name."""
    if request.method == "GET":
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

    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
# @login_required
@require_http_methods(["POST"])
def trigger_syncer(request):
    """Trigger syncer script for AreTomo3 or denoise processing."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            session_name = data.get("session_name")
            run_number = data.get("run_number")
            job_id = data.get("job_id")
            syncer_type = data.get("syncer_type", "aretomo3")  # Default to aretomo3

            if not session_name or not run_number:
                return JsonResponse({"error": "Missing session_name or run_number"}, status=400)

            # Determine which syncer script to use
            if syncer_type == "denoise":
                syncer_script = "denoiset/syncer.py"
            else:
                syncer_script = "aretomo3/syncer.py"

            workflow_dir = Path(__file__).parent.parent.parent
            syncer_script_path = workflow_dir / "processors" / syncer_script

            # Run the syncer with job tracking and continuous mode
            subprocess.Popen(
                [
                    "python",
                    str(syncer_script_path),
                    "--session",
                    session_name,
                    "--run",
                    f"run{run_number.zfill(3)}",
                    "--job-id",
                    job_id if job_id else "",
                    "--continuous",
                ],  # Add continuous mode
                env=dict(os.environ, PYTHONPATH=workflow_dir.resolve()),
            )

            logger.info(
                f"Started {syncer_type} syncer for session {session_name}, run {run_number}, tracking job {job_id}"
            )

            return JsonResponse(
                {
                    "message": f"{syncer_type.capitalize()} syncer started successfully",
                    "session": session_name,
                    "run": run_number,
                    "job_id": job_id,
                    "status": "running",
                }
            )

        except Exception as e:
            logger.error(f"Failed to start syncer: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)
