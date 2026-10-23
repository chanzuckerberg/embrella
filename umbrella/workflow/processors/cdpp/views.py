"""
Custom API views for the cdpp processor.

Provides the dynamic form options: the session's AreTomo3 runs the pipeline can import.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from processes.models import ProcRun

# AreTomo3 runs are recorded under this processing plan.
ARETOMO3_PLAN_NAME = "czii-live"


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
