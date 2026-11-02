"""
Custom API views for the cdpp processor.

- Dynamic form options: the session's AreTomo3 runs the pipeline can import.
- The pipeline registry (/cdpp/v1/pipelines/): one row per cdpp run, for cdpp-web.
"""

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import JobLog, PipeInPlan, ProcRun
from processes.services.cluster_resolver import cluster_id_from_parameters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from stores.models import Cluster, PathType, resolve_review_path

# AreTomo3 runs are recorded under this processing plan.
ARETOMO3_PLAN_NAME = "czii-live"
CDPP_PLAN_NAME = "czii-cdpp"


@require_http_methods(["GET"])
def get_dynamic_options(request, session_id: str = None) -> JsonResponse:
    """
    Dynamic dropdown options for the cdpp form.

    Returns:
        {"success": true, "options": {"aretomo3_runs": [{"value": "run001", "label": "run001", "description": "..."}]}}
    """
    options = {}
    if session_id:
        runs = ProcRun.objects.filter(msi_session__name=session_id, proc_plan__name=ARETOMO3_PLAN_NAME).order_by(
            "-created_at"
        )
        options["aretomo3_runs"] = [
            {
                "value": run.name,
                "label": run.name,
                "description": f"Created {run.created_at.strftime('%Y-%m-%d %H:%M')}",
            }
            for run in runs
        ]

    return JsonResponse({"success": True, "options": options})


def _latest_execution(proc_run):
    """The run's current execution (each relaunch restarts it in place), or None."""
    executions = sorted(proc_run.pipe_executions.all(), key=lambda execution: execution.updated_at, reverse=True)
    return executions[0] if executions else None


def _job_ids(execution) -> set:
    """The execution's job and every earlier attempt's: whoever launched any of them launched the run."""
    if execution is None:
        return set()
    attempts = (execution.parameters or {}).get("_attempts") or []
    return {execution.job_id, *(attempt.get("job_id") for attempt in attempts)} - {None}


def _plan_dirname(plan_name: str):
    """The processing directory name of the software behind a plan (e.g. czii-isonet2 -> isonet2)."""
    step = PipeInPlan.objects.filter(plan__name=plan_name).select_related("pipe__software").order_by("step").first()
    return step.pipe.software.dirname if step else None


def _run_url(cluster, msi_session, dirname, run_name):
    """The file-server URL of a run directory (the proc_url template), or None if it doesn't resolve.

    Resolved for a server-side fetch: cdpp-web reads pipeline files from here when the cluster
    filesystem isn't mounted where it runs.
    """
    if cluster is None or not dirname or not run_name:
        return None
    try:
        url = resolve_review_path(
            "proc_url", cluster, msi_session, backend_fetch=True, proc_software=dirname, proc_run=run_name
        )
    except (PathType.DoesNotExist, ValidationError, ValueError):
        return None
    if not url or "{" in url:
        return None
    return url if url.endswith("/") else f"{url}/"


def _build_pipeline(proc_run, execution) -> dict:
    from workflow.processors import get_processor

    parameters = (execution.parameters if execution else None) or {}
    cluster_id = cluster_id_from_parameters(parameters)
    output_dir = (parameters.get("_cdpp") or {}).get("dir")
    if not output_dir:
        base = get_processor("cdpp").get_processing_base_path(cluster=cluster_id)
        output_dir = f"{base}/{proc_run.msi_session.name}/{proc_run.name}"
    trees = (parameters.get("_reserved_runs") or {}).get("trees") or {}

    cluster = Cluster.objects.filter(cluster_id=cluster_id).first() if cluster_id else None
    session = proc_run.msi_session
    output_url = _run_url(cluster, session, _plan_dirname(CDPP_PLAN_NAME), proc_run.name)

    return {
        "session_name": session.name,
        "run_name": proc_run.name,
        "cluster_id": cluster_id,
        "status": execution.status if execution else "pending",
        "created_at": proc_run.created_at.isoformat(),
        "proc_run_id": proc_run.id,
        "config_path": f"{output_dir}/pipeline.yaml",
        "output_dir": output_dir,
        "output_url": output_url,
        "config_url": f"{output_url}pipeline.yaml" if output_url else None,
        "trees": {
            name: {
                "run": tree.get("run"),
                "dir": tree.get("dir"),
                "reused": tree.get("reused"),
                "url": _run_url(cluster, session, _plan_dirname(tree.get("plan") or ""), tree.get("run")),
            }
            for name, tree in trees.items()
        },
    }


@extend_schema(
    methods=["GET"],
    tags=["cdpp Pipelines"],
    description=(
        "List cdpp pipeline runs (one row per ProcRun under the czii-cdpp plan), with the config path, "
        "output directory and the tool-tree runs each wrote into, plus their file-server URLs "
        "(`output_url`, `config_url`, `trees.*.url`; null where the cluster's proc_url doesn't resolve). "
        "Staff see every run; other users see the runs they launched."
    ),
    parameters=[
        OpenApiParameter(
            name="session_id",
            required=False,
            type=OpenApiTypes.STR,
            description="Filter to a single MsiSession.name.",
        ),
        OpenApiParameter(
            name="status",
            required=False,
            type=OpenApiTypes.STR,
            description=(
                "Filter by execution status (submitted, running, completed, failed, cancelled, pending); "
                "comma-separated for several. Omit or 'all' for every run."
            ),
        ),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET"])
def list_cdpp_pipelines(request) -> JsonResponse:
    """List cdpp pipeline runs.

    Query params:
        session_id: filter to a single MsiSession.name
        status: execution status, comma-separated; omit or 'all' for every run
    """
    qs = (
        ProcRun.objects.filter(proc_plan__name=CDPP_PLAN_NAME)
        .select_related("msi_session")
        .prefetch_related("pipe_executions")
        .order_by("-created_at")
    )
    session_id = request.GET.get("session_id")
    if session_id:
        qs = qs.filter(msi_session__name=session_id)

    runs = [(proc_run, _latest_execution(proc_run)) for proc_run in qs]

    if not request.user.is_staff:
        job_ids = set().union(*(_job_ids(execution) for _, execution in runs))
        mine = set(JobLog.objects.filter(job_id__in=job_ids, user=request.user).values_list("job_id", flat=True))
        runs = [(proc_run, execution) for proc_run, execution in runs if _job_ids(execution) & mine]

    pipelines = [_build_pipeline(proc_run, execution) for proc_run, execution in runs]

    statuses = {s.strip() for s in request.GET.get("status", "").split(",") if s.strip()} - {"all"}
    if statuses:
        pipelines = [pipeline for pipeline in pipelines if pipeline["status"] in statuses]

    return JsonResponse({"success": True, "pipelines": pipelines})
