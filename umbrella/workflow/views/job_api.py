"""
Job API endpoints.

These views provide RESTful API endpoints for job listing, filtering,
and bulk operations on SLURM jobs across compute clusters.
"""

import json
from collections import Counter
from datetime import timedelta

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from processes.models import JobLog, PipeExecution, SyncerLog, SyncerProcess
from processes.services.cluster_resolver import cluster_id_from_parameters, get_default_cluster_id
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from stores.models import Cluster
from umbrella_logger import logger

from common import clusterio

from ..agent import RemoteJobSubmitter, StatusChecker
from .constants import (
    LABEL_TO_SLURM_STATE,
    SLURM_STATE_TO_LABEL,
)
from .utils import format_job_output


def calculate_duration(start_time, end_time):
    """Calculate human-readable duration between two timestamps."""
    if not start_time or not end_time:
        return None

    delta = end_time - start_time
    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        return None
    elif total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_jobs_list(request):
    """
    Enhanced jobs list endpoint that:
    1. Fetches live job data from SLURM (squeue)
    2. Combines with historical data from PipeExecution model
    3. Supports filtering by user, status, job name, etc.
    4. Supports cluster selection (czii/bruno)
    5. Includes historical jobs (completed/failed) from PipeExecution
    """
    try:
        cluster_id = request.GET.get("cluster_id") or get_default_cluster_id()
        if not Cluster.objects.filter(cluster_id=cluster_id, is_active=True).exists():
            return JsonResponse({"error": f"Unknown or inactive cluster_id: {cluster_id}"}, status=400)

        # Get filter parameters
        raw_q_param = request.GET.get("q", None)
        filters = json.loads(raw_q_param) if raw_q_param else []

        # Get direct search parameters (from text search inputs)
        job_id_search = request.GET.get("job_id", "").strip()
        job_name_search = request.GET.get("job_name", "").strip().lower()

        # Parse filters, pagination, and sorting from q parameter
        filter_dict = {}
        page = 1
        page_size = 25
        sort_by = None
        sort_asc = True
        if isinstance(filters, list):
            for filter_item in filters:
                category = filter_item.get("category")
                value = filter_item.get("value", [])

                # Handle pagination
                if category == "page":
                    page = int(value[0] if isinstance(value, list) else value)
                elif category == "pageSize":
                    page_size = int(value[0] if isinstance(value, list) else value)
                # Handle sorting
                elif category == "sort":
                    sort_by = value[0] if isinstance(value, list) else value
                elif category == "asc":
                    sort_asc = bool(value[0] if isinstance(value, list) else value)
                # Handle filters - map lowercase category to uppercase filter key
                elif category == "user":
                    filter_dict["USER"] = value
                elif category == "status":
                    filter_dict["STATUS"] = value
                elif category == "cluster":
                    filter_dict["CLUSTER"] = value
                elif category == "jobName":
                    filter_dict["JOB_NAME"] = value
                elif category == "partition":
                    filter_dict["PARTITION"] = value
                elif category == "completedDateRange":
                    filter_dict["DATE_RANGE"] = value

        # Fetch live jobs from SLURM
        checker = None
        try:
            checker = StatusChecker(
                cluster_id=cluster_id,
                auth=clusterio.get_auth_service_user(),
            )
            checker.connect()
            output, error = checker.track_jobs(job_name=None, all=True)
            live_jobs = format_job_output(output) if output else []
        except Exception as e:
            logger.error(f"Error fetching live jobs from {cluster_id}: {str(e)}")
            live_jobs = []
        finally:
            if checker is not None:
                checker.close()

        # Fetch PipeExecution data for workflow-launched jobs
        pipe_executions = PipeExecution.objects.select_related(
            "proc_run",
            "proc_run__msi_session",
            "pipe_in_plan",
            "pipe_in_plan__pipe",
            "pipe_in_plan__pipe__software",
        ).all()

        # Apply date range filter to historical jobs
        date_range_filter = None
        if "DATE_RANGE" in filter_dict:
            date_filter = filter_dict["DATE_RANGE"][0] if filter_dict["DATE_RANGE"] else None
            if date_filter == "last_1_day":
                date_range_filter = dj_timezone.now() - timedelta(days=1)
            elif date_filter == "last_7_days":
                date_range_filter = dj_timezone.now() - timedelta(days=7)
            elif date_filter == "last_30_days":
                date_range_filter = dj_timezone.now() - timedelta(days=30)

        if date_range_filter:
            pipe_executions = pipe_executions.filter(completed_at__gte=date_range_filter)

        # Create a mapping of job_id -> PipeExecution for quick lookup
        pipe_exec_map = {exec.job_id: exec for exec in pipe_executions if exec.job_id}

        # Create a mapping of job_id -> JobLog for user information lookup
        job_logs = JobLog.objects.filter(job_id__isnull=False).select_related("user")
        job_log_map = {log.job_id: log for log in job_logs}

        # Get set of live job IDs (include both full ID and base ID for hetjobs)
        live_job_ids = set()
        for job in live_jobs:
            job_id = job.get("JOBID")
            if job_id:
                live_job_ids.add(job_id)
                # Also add base job ID for hetjobs (e.g., "9232+0" -> "9232")
                if "+" in job_id:
                    live_job_ids.add(job_id.split("+")[0])

        # NOTE: Status updates are now handled by the JobStatusSyncer which uses sacct
        # for accurate timing. The old code below has been removed:
        # - It was setting completed_at to "now" which gave inaccurate durations
        # - It assumed all jobs not in queue were "completed" (could be failed/cancelled)
        # The JobStatusSyncer polls sacct and gets actual start/end times from SLURM.

        # Combine live jobs with PipeExecution data
        combined_jobs = []
        for job in live_jobs:
            job_id = job.get("JOBID")
            # Handle SLURM hetjob format (e.g., "9232+0" -> base job "9232")
            base_job_id = job_id.split("+")[0] if job_id and "+" in job_id else job_id
            pipe_exec = pipe_exec_map.get(job_id) or pipe_exec_map.get(base_job_id)

            # Apply status filter if specified
            if "STATUS" in filter_dict:
                # Convert full labels to SLURM state names for comparison
                allowed_states = [LABEL_TO_SLURM_STATE.get(label, label) for label in filter_dict["STATUS"]]
                if job.get("ST") not in allowed_states:
                    continue

            # Apply user filter if specified (for live jobs)
            if "USER" in filter_dict:
                username_without_domain = job.get("USER", "").split("@")[0]
                if username_without_domain not in filter_dict["USER"]:
                    continue

            # Apply partition filter if specified
            if "PARTITION" in filter_dict:
                if job.get("PARTITION") not in filter_dict["PARTITION"]:
                    continue

            # Apply cluster filter if specified
            if "CLUSTER" in filter_dict:
                job_cluster = cluster_id_from_parameters(pipe_exec.parameters) if pipe_exec else cluster_id
                if job_cluster not in filter_dict["CLUSTER"]:
                    continue

            # Apply job_id search filter (substring match)
            if job_id_search:
                if job_id_search not in str(job.get("JOBID", "")):
                    continue

            # Get job name from JobLog if available (full name like "aretomo3_24nov10_run001_vol001")
            # Otherwise fall back to software name or SLURM's NAME field
            job_log = job_log_map.get(job_id)
            if job_log and job_log.job_name:
                job_name = job_log.job_name
            elif pipe_exec and pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
                # Use software name as fallback
                job_name = (
                    pipe_exec.pipe_in_plan.pipe.software.name
                    if pipe_exec.pipe_in_plan.pipe.software
                    else pipe_exec.pipe_in_plan.pipe.name
                )
            else:
                job_name = job.get("NAME")

            # Apply job_name search filter (case-insensitive substring match)
            if job_name_search:
                if job_name_search not in (job_name or "").lower():
                    continue

            # Get processor name for syncer support detection
            processor = None
            if pipe_exec and pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
                software = pipe_exec.pipe_in_plan.pipe.software
                processor = software.processor_class or software.name if software else None

            # Get session name if available
            session = None
            if pipe_exec and pipe_exec.proc_run and pipe_exec.proc_run.msi_session:
                session = pipe_exec.proc_run.msi_session.name

            combined_job = {
                "job": {
                    "id": job_id,
                    "name": job_name,
                },
                "jobName": job_name,
                "user": job.get("USER", "").split("@")[0],  # Strip domain
                "status": SLURM_STATE_TO_LABEL.get(job.get("ST"), job.get("ST")),  # Convert to readable label
                "timeUsed": job.get("TIME"),
                "timeLeft": job.get("TIMELEFT"),
                "nodes": job.get("NODES"),
                "partition": job.get("PARTITION"),
                "nodeList": job.get("NODELIST(REASON)"),
                # Prefer the PipeExecution's recorded cluster (truth); fall back
                # to the queried cluster for jobs not launched via our workflow.
                "cluster": cluster_id_from_parameters(pipe_exec.parameters) if pipe_exec else cluster_id,
                "submittedAt": pipe_exec.submitted_at.isoformat() if pipe_exec and pipe_exec.submitted_at else None,
                "parameters": pipe_exec.parameters if pipe_exec else None,
                "errorMessage": pipe_exec.error_message if pipe_exec else None,
                "isWorkflowLaunched": bool(pipe_exec),  # True if job was launched via workflow execution system
                "processor": processor,
                "session": session,
            }
            combined_jobs.append(combined_job)

        # Determine if we should include historical jobs
        # Only include them if status filter explicitly includes completed/failed/cancelled
        should_include_historical = False
        if "STATUS" in filter_dict:
            historical_statuses = {"Completed", "Failed", "Cancelled"}
            if historical_statuses.intersection(set(filter_dict["STATUS"])):
                should_include_historical = True
        # If no status filter is specified, we default to NOT showing historical jobs

        # Add historical jobs from PipeExecution that are no longer in SLURM queue
        if should_include_historical:
            for pipe_exec in pipe_executions:
                if pipe_exec.job_id and pipe_exec.job_id not in live_job_ids:
                    # Apply job_id search filter (substring match)
                    if job_id_search:
                        if job_id_search not in str(pipe_exec.job_id):
                            continue

                    # This is a historical job that's no longer in SLURM queue
                    # Map PipeExecution status to SLURM-like labels
                    status_map = {
                        "completed": "Completed",
                        "failed": "Failed",
                        "cancelled": "Cancelled",
                    }
                    status = status_map.get(pipe_exec.status, pipe_exec.status.capitalize())

                    # Apply status filter
                    if status not in filter_dict["STATUS"]:
                        continue

                    # Apply cluster filter
                    if "CLUSTER" in filter_dict:
                        if cluster_id_from_parameters(pipe_exec.parameters) not in filter_dict["CLUSTER"]:
                            continue

                    # Get user from JobLog
                    job_log = job_log_map.get(pipe_exec.job_id)
                    if job_log and job_log.user:
                        user = job_log.user.username
                    else:
                        user = "unknown"

                    # Apply user filter
                    if "USER" in filter_dict and user not in filter_dict["USER"]:
                        continue

                    # Get job name from JobLog if available (full name from RunContext)
                    # Otherwise fall back to software name
                    job_log = job_log_map.get(pipe_exec.job_id)
                    if job_log and job_log.job_name:
                        job_name = job_log.job_name
                    elif pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
                        job_name = (
                            pipe_exec.pipe_in_plan.pipe.software.name
                            if pipe_exec.pipe_in_plan.pipe.software
                            else pipe_exec.pipe_in_plan.pipe.name
                        )
                    else:
                        job_name = "unknown"

                    # Apply job name filter (dropdown)
                    if "JOB_NAME" in filter_dict and job_name not in filter_dict["JOB_NAME"]:
                        continue

                    # Apply job_name search filter (case-insensitive substring match)
                    if job_name_search:
                        if job_name_search not in (job_name or "").lower():
                            continue

                    # Get processor name from pipe_in_plan (use processor_class for syncer support detection)
                    processor = None
                    if pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe and pipe_exec.pipe_in_plan.pipe.software:
                        software = pipe_exec.pipe_in_plan.pipe.software
                        processor = software.processor_class or software.name

                    # Get session name from proc_run
                    session = None
                    if pipe_exec.proc_run and pipe_exec.proc_run.msi_session:
                        session = pipe_exec.proc_run.msi_session.name

                    combined_job = {
                        "job": {
                            "id": pipe_exec.job_id,
                            "name": job_name,
                        },
                        "jobName": job_name,
                        "user": user,
                        "status": status,
                        "timeUsed": "-",
                        "timeLeft": "-",
                        "nodes": "-",
                        "partition": "-",
                        "nodeList": "-",
                        "cluster": cluster_id_from_parameters(pipe_exec.parameters),
                        "submittedAt": pipe_exec.submitted_at.isoformat() if pipe_exec.submitted_at else None,
                        "completedAt": pipe_exec.completed_at.isoformat() if pipe_exec.completed_at else None,
                        "duration": calculate_duration(
                            pipe_exec.started_at or pipe_exec.submitted_at, pipe_exec.completed_at
                        ),
                        "processor": processor,
                        "session": session,
                        "hasLogs": bool(pipe_exec.stdout_log or pipe_exec.stderr_log),
                        "parameters": pipe_exec.parameters,
                        "errorMessage": pipe_exec.error_message,
                        "isWorkflowLaunched": True,
                    }
                    combined_jobs.append(combined_job)

            # Also add historical jobs from JobLog (legacy system) that don't have PipeExecutions
            # Get all job IDs that we've already included (from live jobs + PipeExecutions)
            included_job_ids = {job.get("job", {}).get("id") for job in combined_jobs}

            # Query JobLog entries with date range filter
            legacy_job_logs = JobLog.objects.filter(job_id__isnull=False).select_related("user")
            if date_range_filter:
                legacy_job_logs = legacy_job_logs.filter(created_at__gte=date_range_filter)

            # Add legacy JobLog entries that aren't already in results
            for job_log in legacy_job_logs:
                if job_log.job_id in included_job_ids:
                    continue  # Skip if already included from PipeExecution

                # Apply job_id search filter (substring match)
                if job_id_search:
                    if job_id_search not in str(job_log.job_id or ""):
                        continue

                # Apply user filter
                user = job_log.user.username if job_log.user else "unknown"
                if "USER" in filter_dict and user not in filter_dict["USER"]:
                    continue

                # Apply job name filter (dropdown)
                job_name = job_log.job_name or "unknown"
                if "JOB_NAME" in filter_dict and job_name not in filter_dict["JOB_NAME"]:
                    continue

                # Apply job_name search filter (case-insensitive substring match)
                if job_name_search:
                    if job_name_search not in (job_name or "").lower():
                        continue

                # Legacy jobs are assumed completed (we don't have detailed status)
                status = "Completed"
                if job_log.error_message:
                    status = "Failed"

                # Apply status filter
                if status not in filter_dict["STATUS"]:
                    continue

                # Apply cluster filter (JobLog has no cluster info; assume request cluster_id)
                if "CLUSTER" in filter_dict and cluster_id not in filter_dict["CLUSTER"]:
                    continue

                combined_job = {
                    "job": {
                        "id": job_log.job_id,
                        "name": job_name,
                    },
                    "jobName": job_name,
                    "user": user,
                    "status": status,
                    "timeUsed": "-",
                    "timeLeft": "-",
                    "nodes": "-",
                    "partition": "-",
                    "nodeList": "-",
                    "cluster": cluster_id,  # Assume same cluster (we don't have cluster info in JobLog)
                    "submittedAt": job_log.created_at.isoformat() if job_log.created_at else None,
                    "completedAt": None,  # JobLog doesn't track completion time
                    "duration": None,  # Can't calculate without completion time
                    "processor": None,  # JobLog doesn't have processor info
                    "session": None,  # JobLog doesn't have session info
                    "hasLogs": False,  # JobLog doesn't store execution logs
                    "parameters": job_log.parameters,
                    "errorMessage": job_log.error_message,
                    "isWorkflowLaunched": not job_log.advanced,  # non-advanced jobs were workflow launched
                }
                combined_jobs.append(combined_job)

        # Apply sorting if specified
        if sort_by:
            # Map frontend column IDs to job dict keys
            sort_key_map = {
                "jobId": lambda job: int(job["job"]["id"]) if job["job"]["id"].isdigit() else 0,
                "jobName": lambda job: job["jobName"].lower() if job["jobName"] else "",
                "user": lambda job: job["user"].lower() if job["user"] else "",
                "status": lambda job: job["status"].lower() if job["status"] else "",
                "timeUsed": lambda job: job["timeUsed"] if job["timeUsed"] else "",
                "timeLeft": lambda job: job["timeLeft"] if job["timeLeft"] else "",
                "cluster": lambda job: job["cluster"] if job["cluster"] else "",
                "partition": lambda job: job["partition"] if job["partition"] else "",
                "nodes": lambda job: job["nodes"] if job["nodes"] else "",
                "submittedAt": lambda job: job.get("submittedAt") or "",
                "completedAt": lambda job: job.get("completedAt") or "",
                "duration": lambda job: job.get("duration") or "",
                "processor": lambda job: (job.get("processor") or "").lower(),
                "session": lambda job: (job.get("session") or "").lower(),
            }

            if sort_by in sort_key_map:
                combined_jobs.sort(key=sort_key_map[sort_by], reverse=not sort_asc)
        else:
            # Default sort by job ID descending
            sort_by = "jobId"
            sort_asc = False
            combined_jobs.sort(key=lambda job: int(job["job"]["id"]) if job["job"]["id"].isdigit() else 0, reverse=True)

        # Apply pagination
        total_count = len(combined_jobs)
        paginator = Paginator(combined_jobs, page_size, orphans=3)

        try:
            paginated_jobs = paginator.page(page)
        except PageNotAnInteger:
            paginated_jobs = paginator.page(1)
        except EmptyPage:
            paginated_jobs = paginator.page(paginator.num_pages)

        return JsonResponse(
            {
                "result": list(paginated_jobs),
                "pagination": {
                    "page": paginated_jobs.number,
                    "pageSize": page_size,
                    "totalPages": paginator.num_pages,
                    "totalResults": total_count,
                },
                "sortBy": {
                    "sort": sort_by,
                    "asc": sort_asc,
                },
            }
        )

    except Exception as e:
        logger.exception(f"Error in get_jobs_list: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Get available filter options for jobs",
    description="Returns available filter values for job management filters",
    parameters=[
        OpenApiParameter(
            name="cluster_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Cluster to query (czii or bruno)",
            required=False,
            default="czii",
        ),
    ],
    responses={
        200: OpenApiResponse(description="Filter options retrieved successfully"),
        500: OpenApiResponse(description="Error retrieving filter options"),
    },
)
def get_jobs_filterlist(request):
    """
    Returns available filter options for job management:
    - Users (from live SLURM jobs)
    - Job statuses (from SLURM states + PipeExecution)
    - Clusters (czii, bruno)
    - Job names (from PipeExecution)
    - Partitions (from live job data)
    - Date ranges
    """
    try:
        cluster_id = request.GET.get("cluster_id") or get_default_cluster_id()

        # SLURM state to label mapping
        SLURM_STATE_TO_LABEL_LOCAL = {
            "RUNNING": "Running",
            "PENDING": "Pending",
            "COMPLETING": "Completing",
            "COMPLETED": "Completed",
            "FAILED": "Failed",
            "CANCELLED": "Cancelled",
            "TIMEOUT": "Timeout",
        }

        # Parse current filter state from q parameter
        raw_q_param = request.GET.get("q", None)
        filters = json.loads(raw_q_param) if raw_q_param else []

        # Build selected_filters dict to track active filters
        selected_filters = {}
        for filter_item in filters:
            category = filter_item.get("category")
            value = filter_item.get("value", [])
            if category and value:
                selected_filters[category] = set(value)

        # Get unique job names from JobLog (full RunContext names)
        # Fall back to software names from PipeExecution if JobLog not available
        job_logs = JobLog.objects.filter(job_name__isnull=False).values_list("job_name", flat=True).distinct()
        job_names = set(job_logs)

        # Also include software names as fallback for jobs without JobLog entries
        pipe_executions = PipeExecution.objects.select_related(
            "pipe_in_plan",
            "pipe_in_plan__pipe",
            "pipe_in_plan__pipe__software",
        ).all()
        job_names.update(
            {
                exec.pipe_in_plan.pipe.software.name
                for exec in pipe_executions
                if exec.pipe_in_plan and exec.pipe_in_plan.pipe and exec.pipe_in_plan.pipe.software
            }
        )

        # Fetch live jobs to get partitions and statuses
        try:
            checker = StatusChecker(
                cluster_id=cluster_id,
                auth=clusterio.get_auth_service_user(),
            )
            checker.connect()
            output, error = checker.track_jobs(job_name=None, all=True)
            live_jobs = format_job_output(output) if output else []
            checker.close()

            # Get unique partitions from live jobs
            partitions = list({job.get("PARTITION") for job in live_jobs if job.get("PARTITION")})
        except Exception as e:
            logger.error(f"Error fetching live job data for filters: {str(e)}")
            partitions = []
            live_jobs = []

        # Fetch PipeExecution data and combine with live jobs for counting
        pipe_exec_map = {exec.job_id: exec for exec in pipe_executions if exec.job_id}
        live_job_ids = {job.get("JOBID") for job in live_jobs}

        # Create mapping for JobLog user lookup
        job_logs = JobLog.objects.filter(job_id__isnull=False).select_related("user")
        job_log_map = {log.job_id: log for log in job_logs}

        # Combine live jobs with PipeExecution data
        all_jobs = []
        for job in live_jobs:
            job_id = job.get("JOBID")
            pipe_exec = pipe_exec_map.get(job_id)

            # Use job name from JobLog if available (full RunContext name)
            # Otherwise fall back to software name or SLURM NAME
            job_log = job_log_map.get(job_id)
            if job_log and job_log.job_name:
                job_name = job_log.job_name
            elif pipe_exec and pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
                job_name = (
                    pipe_exec.pipe_in_plan.pipe.software.name
                    if pipe_exec.pipe_in_plan.pipe.software
                    else pipe_exec.pipe_in_plan.pipe.name
                )
            else:
                job_name = job.get("NAME")

            all_jobs.append(
                {
                    "user": job.get("USER", "").split("@")[0],
                    "status": SLURM_STATE_TO_LABEL_LOCAL.get(job.get("ST"), job.get("ST")),
                    "partition": job.get("PARTITION"),
                    "jobName": job_name,
                    "cluster": cluster_id_from_parameters(pipe_exec.parameters) if pipe_exec else cluster_id,
                    "submittedAt": pipe_exec.submitted_at if pipe_exec else None,
                }
            )

        # Add historical jobs from PipeExecution for counting
        for pipe_exec in pipe_executions:
            if pipe_exec.job_id and pipe_exec.job_id not in live_job_ids:
                status_map = {
                    "completed": "Completed",
                    "failed": "Failed",
                    "cancelled": "Cancelled",
                }
                status = status_map.get(pipe_exec.status, pipe_exec.status.capitalize())
                # Use software name
                if pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
                    job_name = (
                        pipe_exec.pipe_in_plan.pipe.software.name
                        if pipe_exec.pipe_in_plan.pipe.software
                        else pipe_exec.pipe_in_plan.pipe.name
                    )
                else:
                    job_name = "unknown"

                # Get user from JobLog
                job_log = job_log_map.get(pipe_exec.job_id)
                if job_log and job_log.user:
                    user = job_log.user.username
                else:
                    user = "unknown"

                all_jobs.append(
                    {
                        "user": user,
                        "status": status,
                        "partition": "-",
                        "jobName": job_name,
                        "cluster": cluster_id_from_parameters(pipe_exec.parameters),
                        "submittedAt": pipe_exec.submitted_at,
                    }
                )

        # Calculate counts for each filter category
        user_counts = Counter(job["user"] for job in all_jobs if job.get("user"))
        status_counts = Counter(job["status"] for job in all_jobs if job.get("status"))
        partition_counts = Counter(job["partition"] for job in all_jobs if job.get("partition"))
        jobname_counts = Counter(job["jobName"] for job in all_jobs if job.get("jobName"))

        # Build filter options with real counts and selection state

        # User filters (from live jobs only - historical jobs don't have user info)
        unique_users = {job["user"] for job in all_jobs if job.get("user") and job.get("user") != "unknown"}
        user_filters = [
            {
                "name": username,
                "count": user_counts.get(username, 0),
                "selected": username in selected_filters.get("user", set()),
            }
            for username in sorted(unique_users)
        ]

        # Status filters
        status_labels = ["Running", "Pending", "Completing", "Completed", "Failed", "Cancelled", "Timeout"]
        status_filters = [
            {
                "name": label,
                "count": status_counts.get(label, 0),
                "selected": label in selected_filters.get("status", set()),
            }
            for label in status_labels
        ]

        # Job name filters
        job_name_filters = [
            {
                "name": name,
                "count": jobname_counts.get(name, 0),
                "selected": name in selected_filters.get("jobName", set()),
            }
            for name in job_names
            if name
        ]

        # Partition filters
        partition_filters = [
            {
                "name": partition,
                "count": partition_counts.get(partition, 0),
                "selected": partition in selected_filters.get("partition", set()),
            }
            for partition in partitions
        ]

        # Cluster options
        cluster_counts = Counter(j["cluster"] for j in all_jobs if j.get("cluster"))
        selected_clusters = selected_filters.get("cluster", set())
        cluster_filters = [
            {
                "name": c.cluster_id,
                "count": cluster_counts.get(c.cluster_id, 0),
                "selected": c.cluster_id in selected_clusters,
            }
            for c in Cluster.objects.filter(is_active=True).order_by("cluster_id")
        ]

        # Date range options (counts would require date filtering logic)
        date_filters = [
            {
                "name": "last_1_day",
                "count": 0,
                "selected": "last_1_day" in selected_filters.get("completedDateRange", set()),
            },
            {
                "name": "last_7_days",
                "count": 0,
                "selected": "last_7_days" in selected_filters.get("completedDateRange", set()),
            },
            {
                "name": "last_30_days",
                "count": 0,
                "selected": "last_30_days" in selected_filters.get("completedDateRange", set()),
            },
        ]

        return JsonResponse(
            {
                "filters": {
                    "user": user_filters,
                    "status": status_filters,
                    "cluster": cluster_filters,
                    "jobName": job_name_filters,
                    "partition": partition_filters,
                    "completedDateRange": date_filters,
                },
            }
        )

    except Exception as e:
        logger.exception(f"Error in get_jobs_filterlist: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Cancel multiple jobs",
    description="Cancel one or more SLURM jobs by job ID. Requires the user to have completed SSH key setup for the cluster.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "job_ids": {"type": "array", "items": {"type": "string"}},
                "cluster_id": {"type": "string"},
            },
            "required": ["job_ids", "cluster_id"],
        },
    },
    responses={
        200: OpenApiResponse(description="Jobs cancelled successfully"),
        400: OpenApiResponse(description="Invalid request"),
        403: OpenApiResponse(description="SSH setup required"),
        500: OpenApiResponse(description="Error cancelling jobs"),
    },
)
def bulk_cancel_jobs(request):
    """
    Cancel multiple SLURM jobs at once.

    Authenticates as the requesting Django user using the cluster username
    stored in UserClusterCredentials. Returns 403 with ssh_setup_required if
    the user has not yet set up credentials for the cluster, which the
    frontend uses to open the SSH setup modal.
    """
    from accounts.cluster_usernames import MissingClusterCredentialsError

    try:
        data = request.data
        job_ids = data.get("job_ids", [])
        cluster_id = data.get("cluster_id", "czii")

        if not job_ids:
            return JsonResponse({"error": "No job IDs provided"}, status=400)

        if cluster_id not in ["czii", "bruno"]:
            return JsonResponse({"error": "Invalid cluster_id"}, status=400)

        try:
            auth, error = clusterio.get_auth_for_user(request.user, cluster_id)
        except MissingClusterCredentialsError:
            return JsonResponse(
                {
                    "error": "SSH key not set up for this user",
                    "ssh_setup_required": True,
                    "cluster_id": cluster_id,
                },
                status=403,
            )
        if error:
            return JsonResponse(error, status=403)

        # Create RemoteJobSubmitter with appropriate auth

        canceler = RemoteJobSubmitter(
            cluster_id=cluster_id,
            auth=auth,
        )

        results = []

        try:
            canceler.connect()

            for job_id in job_ids:
                try:
                    success, message = canceler.cancel(job_id)
                    results.append(
                        {
                            "job_id": job_id,
                            "success": success,
                            "message": message,
                        }
                    )

                    # Update PipeExecution record if cancel was successful
                    if success:
                        pipe_exec = PipeExecution.objects.filter(job_id=job_id).first()
                        if pipe_exec:
                            pipe_exec.status = "cancelled"
                            pipe_exec.completed_at = dj_timezone.now()
                            pipe_exec.save(update_fields=["status", "completed_at"])
                            logger.info(f"Updated PipeExecution for cancelled job {job_id}")

                except Exception as e:
                    results.append(
                        {
                            "job_id": job_id,
                            "success": False,
                            "message": str(e),
                        }
                    )

            successful = sum(1 for r in results if r["success"])

            return JsonResponse(
                {
                    "success": True,
                    "cancelled": successful,
                    "failed": len(results) - successful,
                    "results": results,
                }
            )

        except Exception as e:
            logger.exception(f"Error during bulk cancel: {str(e)}")
            return JsonResponse({"error": f"Connection error: {str(e)}"}, status=500)
        finally:
            canceler.close()

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except clusterio.SSHDisabledError:
        # No cluster access (e.g. demo server) — cancelling jobs is unavailable.
        return JsonResponse(
            {"error": "SSH is disabled on this server", "ssh_disabled": True},
            status=503,
        )
    except Exception as e:
        logger.exception(f"Error in bulk_cancel_jobs: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


# Processors with a syncer, and the label SyncerLog rows carry. The label is
# also the class name under workflow.processors.<processor>.syncer.
SYNCER_TYPES = {
    "aretomo3": "AretomoSyncer",
    "denoiset": "DenoiseSyncer",
}
SYNCER_CLASS_PATH = "workflow.processors.{processor}.syncer.{cls}"


def _get_syncer_status_for_job(job_id: str, pipe_execution: PipeExecution = None):
    """
    Helper to get syncer status for a job.

    Returns dict with:
    - status: running/stopped/completed/failed/null
    - last_heartbeat: ISO timestamp or null
    - can_rerun: boolean indicating if syncer can be re-run
    - syncer_type: the type of syncer (e.g., AretomoSyncer)
    """
    syncer_process = SyncerProcess.objects.filter(job_id=job_id).first()

    if not syncer_process:
        # Check if job supports syncer (is aretomo3 or denoiset)
        if pipe_execution:
            processor_name = None
            if pipe_execution.pipe_in_plan and pipe_execution.pipe_in_plan.pipe:
                software = pipe_execution.pipe_in_plan.pipe.software
                processor_name = software.processor_class or software.name if software else None

            supports_syncer = processor_name in SYNCER_TYPES
            if supports_syncer:
                # No syncer process exists but job supports it
                job_completed = pipe_execution.status in ["completed", "failed"]
                return {
                    "status": None,
                    "last_heartbeat": None,
                    "can_rerun": job_completed,  # Can re-run if job completed
                    "syncer_type": SYNCER_TYPES.get(processor_name),
                }
        return None

    # Determine if re-run is available
    can_rerun = False
    if pipe_execution:
        job_running = pipe_execution.status in ["submitted", "running"]
        job_completed = pipe_execution.status in ["completed", "failed"]

        if job_running:
            # For running jobs: show if syncer stopped unexpectedly
            can_rerun = syncer_process.is_unexpectedly_stopped()
        elif job_completed:
            # For completed/failed jobs: always allow re-run
            can_rerun = True

    return {
        "status": syncer_process.status,
        "last_heartbeat": syncer_process.last_heartbeat.isoformat() if syncer_process.last_heartbeat else None,
        "can_rerun": can_rerun,
        "syncer_type": syncer_process.syncer_type,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Get syncer logs for a job",
    description="Retrieve syncer action logs and status for a specific SLURM job.",
    parameters=[
        OpenApiParameter(name="job_id", type=str, location="path", description="SLURM job ID"),
    ],
    responses={
        200: OpenApiResponse(description="Syncer logs and status"),
        404: OpenApiResponse(description="Job not found"),
        500: OpenApiResponse(description="Error retrieving logs"),
    },
)
def get_syncer_logs(request, job_id: str):
    """
    Get syncer logs for a job.

    Returns:
        {
            "success": true,
            "logs": [
                {
                    "timestamp": "2024-11-10T10:30:00Z",
                    "action_type": "file_found",
                    "message": "Found 5 ZARR files",
                    "metadata": {...}
                },
                ...
            ],
            "syncer_status": {
                "status": "running",
                "last_heartbeat": "2024-11-10T10:35:00Z",
                "can_rerun": false,
                "syncer_type": "AretomoSyncer"
            }
        }
    """
    try:
        # Handle SLURM hetjob format (e.g., "9232+0" -> base job "9232")
        base_job_id = job_id.split("+")[0] if "+" in job_id else job_id

        # Get PipeExecution for the job (try exact match first, then base job ID)
        pipe_exec = (
            PipeExecution.objects.select_related(
                "pipe_in_plan__pipe__software",
            )
            .filter(job_id=job_id)
            .first()
        )

        if not pipe_exec and base_job_id != job_id:
            pipe_exec = (
                PipeExecution.objects.select_related(
                    "pipe_in_plan__pipe__software",
                )
                .filter(job_id=base_job_id)
                .first()
            )

        # Use the job_id that matches the PipeExecution for log lookup
        lookup_job_id = pipe_exec.job_id if pipe_exec else base_job_id

        # Get logs (most recent first, limited to 100)
        logs = SyncerLog.objects.filter(job_id=lookup_job_id).order_by("-timestamp")[:100]

        # Get syncer status
        syncer_status = _get_syncer_status_for_job(lookup_job_id, pipe_exec)

        return JsonResponse(
            {
                "success": True,
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "action_type": log.action_type,
                        "message": log.message,
                        "metadata": log.metadata,
                    }
                    for log in logs
                ],
                "syncer_status": syncer_status,
            }
        )

    except Exception as e:
        logger.exception(f"Error getting syncer logs for job {job_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="Re-run syncer for a job",
    description="Trigger a syncer re-run for a specific SLURM job. This starts a new syncer process to sync output files.",
    parameters=[
        OpenApiParameter(name="job_id", type=str, location="path", description="SLURM job ID"),
    ],
    responses={
        200: OpenApiResponse(description="Syncer started successfully"),
        400: OpenApiResponse(description="Syncer not supported for this job"),
        404: OpenApiResponse(description="Job not found"),
        500: OpenApiResponse(description="Error starting syncer"),
    },
)
def rerun_syncer(request, job_id: str):
    """
    Re-run syncer for a job.

    This will:
    1. Mark any existing syncer process as stopped
    2. Queue a one-shot syncer task
    3. Return success status

    Returns:
        {
            "success": true,
            "message": "Syncer started",
        }
    """
    try:
        # Handle SLURM hetjob format (e.g., "9232+0" -> base job "9232")
        base_job_id = job_id.split("+")[0] if "+" in job_id else job_id

        # Get PipeExecution for the job (try exact match first, then base job ID)
        pipe_exec = (
            PipeExecution.objects.select_related(
                "pipe_in_plan__pipe__software",
                "proc_run__msi_session",
            )
            .filter(job_id=job_id)
            .first()
        )

        if not pipe_exec and base_job_id != job_id:
            pipe_exec = (
                PipeExecution.objects.select_related(
                    "pipe_in_plan__pipe__software",
                    "proc_run__msi_session",
                )
                .filter(job_id=base_job_id)
                .first()
            )

        if not pipe_exec:
            return JsonResponse({"success": False, "error": "Job not found"}, status=404)

        # Use the actual job_id from the PipeExecution for syncer operations
        actual_job_id = pipe_exec.job_id

        # Get processor name
        processor_name = None
        if pipe_exec.pipe_in_plan and pipe_exec.pipe_in_plan.pipe:
            software = pipe_exec.pipe_in_plan.pipe.software
            processor_name = software.processor_class or software.name if software else None

        if processor_name not in SYNCER_TYPES:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Syncer re-run not supported for processor: {processor_name}",
                },
                status=400,
            )

        # Get session and run info
        if not pipe_exec.proc_run or not pipe_exec.proc_run.msi_session:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Could not determine session/run for this job",
                },
                status=400,
            )

        session_name = pipe_exec.proc_run.msi_session.name
        run_name = pipe_exec.proc_run.name

        # Mark any existing syncer as stopped
        SyncerProcess.objects.filter(job_id=actual_job_id, status="running").update(
            status="stopped",
            stopped_at=dj_timezone.now(),
        )

        # Log the re-run action
        SyncerLog.objects.create(
            pipe_execution=pipe_exec,
            job_id=actual_job_id,
            action_type="init",
            message=f"Syncer re-run triggered by user {request.user.username}",
            metadata={
                "triggered_by": request.user.username,
                "session_name": session_name,
                "run_name": run_name,
                "processor": processor_name,
            },
            syncer_type=SYNCER_TYPES[processor_name],
            session_name=session_name,
            run_id=run_name,
        )

        # Same Django-Q task on_job_submit uses. The job is already done, so the
        # task syncs once and stops instead of rescheduling.
        from processes.tasks import start_syncer_monitoring

        from workflow.processors import get_processor

        cluster_id = cluster_id_from_parameters(pipe_exec.parameters)
        base_path = get_processor(processor_name).get_processing_base_path(cluster=cluster_id)

        logger.info(f"Starting syncer re-run for {session_name}/{run_name} (job {actual_job_id})")

        start_syncer_monitoring(
            syncer_class_path=SYNCER_CLASS_PATH.format(processor=processor_name, cls=SYNCER_TYPES[processor_name]),
            base_path=base_path,
            session_name=session_name,
            run_id=run_name,
            job_id=actual_job_id,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Syncer started successfully",
            }
        )

    except Exception as e:
        logger.exception(f"Error re-running syncer for job {job_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
