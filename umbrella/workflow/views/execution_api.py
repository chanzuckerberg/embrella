"""
Generic Pipeline Execution API

Provides RESTful endpoints for executing processing pipelines using the processor registry.
This replaces hardcoded execution logic with a generic, extensible system.
"""

import json

from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import PipeExecution, PipeInPlan, ProcPlan, ProcRun, ProcSoftware
from rest_framework.decorators import api_view
from tem.models import MsiSession
from umbrella_logger import logger

from common import clusterio
from workflow.execution import PipelineExecutor, ValidationError
from workflow.processors import get_processor, list_processors


@require_http_methods(["GET"])
@login_required
def list_available_processors(request):
    """
    List all registered processors.

    GET /workflow/v1/processors/

    Returns:
        {
            "processors": [
                {
                    "name": "aretomo3",
                    "display_name": "AreTomo3",
                    "version": "2024-03-10",
                    "cluster": "czii"
                },
                ...
            ]
        }
    """
    try:
        processors = list_processors()
        processor_list = []

        for name, cls in processors.items():
            # Instantiate to get instance attributes
            instance = cls()

            # Skip processors hidden from list (accessed via other UIs, not dropdown)
            if getattr(instance, "hidden_from_list", False):
                continue

            # Try to get cluster info from database
            try:
                software = ProcSoftware.objects.get(processor_class=name, active=True)
                default_cluster = software.default_cluster
                allowed_clusters = software.allowed_clusters if software.allowed_clusters else ["czii", "bruno"]
            except ProcSoftware.DoesNotExist:
                # Fallback to processor class attributes
                default_cluster = instance.cluster or "czii"
                allowed_clusters = ["czii", "bruno"]

            processor_list.append(
                {
                    "name": instance.name,
                    "display_name": instance.display_name,
                    "version": instance.version,
                    "default_cluster": default_cluster,
                    "allowed_clusters": allowed_clusters,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "processors": processor_list,
            }
        )

    except Exception as e:
        logger.error(f"Error listing processors: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def get_processor_schema(request, processor_name: str):
    """
    Get parameter schema for a specific processor.

    GET /workflow/v1/processors/<name>/schema/

    Returns:
        {
            "success": true,
            "processor": "aretomo3",
            "schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            },
            "slurm_options": {
                "partition": "cpu",
                "nodes": 1,
                ...
            }
        }
    """
    try:
        processor = get_processor(processor_name)

        # Try to get cluster info from database
        try:
            software = ProcSoftware.objects.get(processor_class=processor_name, active=True)
            default_cluster = software.default_cluster
            allowed_clusters = software.allowed_clusters if software.allowed_clusters else ["czii", "bruno"]
        except ProcSoftware.DoesNotExist:
            # Fallback to processor class attributes
            default_cluster = processor.cluster or "czii"
            allowed_clusters = ["czii", "bruno"]

        return JsonResponse(
            {
                "success": True,
                "processor": processor.name,
                "display_name": processor.display_name,
                "version": processor.version,
                "default_cluster": default_cluster,
                "allowed_clusters": allowed_clusters,
                "schema": processor.get_parameter_schema(),
            }
        )

    except ValueError as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=404,
        )

    except Exception as e:
        logger.error(f"Error getting processor schema: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def execute_pipe(request):
    """
    Execute a single pipe in a processing plan.

    POST /workflow/v1/execution/execute/

    Authentication: uses the requesting Django user's cluster credentials
    from UserClusterCredentials. Returns 403 with ssh_setup_required if the
    user has not yet set up credentials for the cluster, which the frontend
    uses to open the SSH setup modal.

    Request body:
        {
            "pipe_in_plan_id": 123,
            "proc_run_id": 456,
            "parameters": {...},
            "cluster_id": "czii"  // Optional: override default cluster (default: "czii")
        }

    Returns:
        {
            "success": true,
            "job_id": "123456",
            "script_path": "/path/to/script.sh",
            "status": "submitted",
            "pipe_execution_id": 789
        }

        OR (if SSH setup required):

        {
            "success": false,
            "error": "SSH key not set up for this user",
            "ssh_setup_required": true,
            "cluster_id": "czii"
        }
    """
    try:
        # Parse request body
        data = json.loads(request.body)

        # Support two formats:
        # 1. Legacy format with IDs: pipe_in_plan_id, proc_run_id
        # 2. New format with names: processor, session_id (name), run_name
        pipe_in_plan_id = data.get("pipe_in_plan_id")
        proc_run_id = data.get("proc_run_id")
        processor_name = data.get("processor")
        session_name = data.get("session_id")  # Actually session name, not ID
        run_name = data.get("run_name")

        parameters = data.get("parameters", {})
        cluster_id = data.get("cluster") or data.get("cluster_id")  # Support both field names

        from accounts.cluster_usernames import MissingClusterCredentialsError

        try:
            auth, error = clusterio.get_auth_for_user(request.user, cluster_id)
        except MissingClusterCredentialsError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "SSH key not set up for this user",
                    "ssh_setup_required": True,
                    "cluster_id": cluster_id,
                },
                status=403,
            )
        if error:
            return JsonResponse(
                {
                    "success": False,
                    **error,
                },
                status=403,
            )

        # If names provided instead of IDs, look them up (and create run if needed)
        if processor_name and session_name and run_name:
            # Look up MSI session
            try:
                msi_session = MsiSession.objects.get(name=session_name)
            except MsiSession.DoesNotExist:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Session '{session_name}' not found",
                    },
                    status=404,
                )

            # Get the processor
            try:
                processor = get_processor(processor_name)
            except ValueError as e:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Invalid processor '{processor_name}': {str(e)}",
                    },
                    status=404,
                )

            # Find plan with this processor
            pipe_in_plan_with_processor = (
                PipeInPlan.objects.filter(
                    pipe__software__processor_class=processor_name,
                )
                .select_related("plan", "pipe", "pipe__software")
                .first()
            )

            if not pipe_in_plan_with_processor:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"No processing plan found with processor '{processor_name}'",
                    },
                    status=404,
                )

            proc_plan = pipe_in_plan_with_processor.plan

            # Get or create the processing run (NOW create it since we're actually submitting)
            proc_run, created = ProcRun.objects.get_or_create(
                msi_session=msi_session,
                name=run_name,
                proc_plan=proc_plan,
                defaults={
                    "created_at": timezone.now(),
                },
            )

            if created:
                logger.info(f"Created new ProcRun: {run_name} for session {session_name} with plan {proc_plan.name}")

            # Find matching pipe_in_plan
            matching_pipe_in_plan = None
            for pip in PipeInPlan.objects.filter(plan=proc_plan).select_related("pipe", "pipe__software"):
                if (
                    hasattr(pip.pipe.software, "processor_class")
                    and pip.pipe.software.processor_class == processor_name
                ):
                    matching_pipe_in_plan = pip
                    break

            if not matching_pipe_in_plan:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"No pipeline step found for processor '{processor_name}' in plan '{proc_plan.name}'",
                    },
                    status=404,
                )

            # Set the IDs for execution
            pipe_in_plan_id = matching_pipe_in_plan.id
            proc_run_id = proc_run.id

        # Validate we have IDs (either provided or looked up)
        if not pipe_in_plan_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "pipe_in_plan_id is required (or provide processor/session_id/run_name)",
                },
                status=400,
            )

        if not proc_run_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "proc_run_id is required (or provide processor/session_id/run_name)",
                },
                status=400,
            )

        if cluster_id not in ["czii", "bruno"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid cluster_id. Must be czii or bruno",
                },
                status=400,
            )

        # Get database objects
        try:
            pipe_in_plan = PipeInPlan.objects.get(id=pipe_in_plan_id)
        except PipeInPlan.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"PipeInPlan with id {pipe_in_plan_id} not found",
                },
                status=404,
            )

        try:
            proc_run = ProcRun.objects.get(id=proc_run_id)
        except ProcRun.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"ProcRun with id {proc_run_id} not found",
                },
                status=404,
            )

        # Use the authenticated user from the request
        # (The view is @login_required so request.user is already a User instance)
        user = request.user

        # Execute the pipe
        executor = PipelineExecutor()

        try:
            result = executor.execute_pipe(
                pipe_in_plan=pipe_in_plan,
                proc_run=proc_run,
                user=user,
                parameters=parameters,
                auth=auth,
                cluster_id=cluster_id,
            )

            return JsonResponse(
                {
                    "success": True,
                    **result,
                }
            )

        except ValidationError as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Parameter validation failed",
                    "validation_errors": e.errors,
                },
                status=400,
            )

        except ValueError as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                },
                status=400,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON in request body",
            },
            status=400,
        )

    except Exception as e:
        logger.error(f"Error executing pipe: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": f"Internal error: {str(e)}",
            },
            status=500,
        )


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def preview_script(request):
    """
    Preview rendered SLURM script WITHOUT submitting to cluster.

    POST /workflow/v1/execution/preview/

    This endpoint validates parameters and renders the script but does NOT:
    - Create any database records (ProcRun, PipeExecution)
    - Submit jobs to SLURM
    - Start monitoring or syncers

    Request body: Same as execute_pipe
        {
            "processor": "aretomo3",
            "session_id": "Grid6_2025-04-22",  # Actually session name
            "run_name": "run001",
            "parameters": {...},
            "cluster": "czii"
        }

    Returns:
        {
            "success": true,
            "script_content": "#!/bin/bash\\n#SBATCH --job-name=...\\n..."
        }
    """
    try:
        # Parse request body
        data = json.loads(request.body)

        processor_name = data.get("processor")
        session_name = data.get("session_id")  # Actually session name
        run_name = data.get("run_name")
        parameters = data.get("parameters", {})
        cluster_id = data.get("cluster") or data.get("cluster_id", "czii")

        # Validate required fields
        if not processor_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "processor is required",
                },
                status=400,
            )

        if not session_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "session_id is required",
                },
                status=400,
            )

        if not run_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "run_name is required",
                },
                status=400,
            )

        # Validate cluster
        if cluster_id not in ["czii", "bruno"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid cluster. Must be czii or bruno",
                },
                status=400,
            )

        # Get processor
        try:
            processor = get_processor(processor_name)
        except ValueError as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Invalid processor '{processor_name}': {str(e)}",
                },
                status=404,
            )

        # Get MSI session
        try:
            msi_session = MsiSession.objects.get(name=session_name)
        except MsiSession.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Session '{session_name}' not found",
                },
                status=404,
            )

        # Build RunContext for preview
        # Create temporary in-memory model instances (not saved to DB)
        from workflow.context import RunContext

        # Find a pipe_in_plan with this processor to get plan and pipe info
        pipe_in_plan_with_processor = (
            PipeInPlan.objects.filter(
                pipe__software__processor_class=processor_name,
            )
            .select_related("plan", "pipe", "pipe__software")
            .first()
        )

        if not pipe_in_plan_with_processor:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"No processing plan found with processor '{processor_name}'",
                },
                status=404,
            )

        proc_plan = pipe_in_plan_with_processor.plan

        # Create temporary ProcRun (not saved, just for preview)
        temp_proc_run = ProcRun(
            name=run_name,
            proc_plan=proc_plan,
            msi_session=msi_session,
        )

        # Use the existing pipe_in_plan from database for context
        temp_pipe_in_plan = pipe_in_plan_with_processor

        context = RunContext(
            proc_run=temp_proc_run,
            pipe_in_plan=temp_pipe_in_plan,
            msi_session=msi_session,
            cluster_id=cluster_id,
            run_number=run_name,
            job_name=f"{processor.name}_{msi_session.name}_{run_name}",
            user=request.user,
            inputs={},  # Preview doesn't need actual input paths
        )

        # Validate parameters
        errors = processor.validate_parameters(parameters)
        if errors:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Parameter validation failed",
                    "validation_errors": errors,
                },
                status=400,
            )

        # Validate SLURM resources
        slurm_errors = processor.validate_slurm_resources(parameters, cluster_id)
        if slurm_errors:
            return JsonResponse(
                {
                    "success": False,
                    "error": "SLURM resource validation failed",
                    "validation_errors": slurm_errors,
                },
                status=400,
            )

        # Render script
        try:
            script_content = processor.render_script(parameters, context)
        except Exception as e:
            logger.error(f"Error rendering script for preview: {e}", exc_info=True)
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to render script: {str(e)}",
                },
                status=500,
            )

        # Return script content
        return JsonResponse(
            {
                "success": True,
                "script_content": script_content,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON in request body",
            },
            status=400,
        )

    except Exception as e:
        logger.error(f"Error previewing script: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": f"Internal error: {str(e)}",
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def get_execution_status(request, execution_id: int):
    """
    Get status of a pipe execution.

    GET /workflow/v1/execution/<id>/status/

    Returns:
        {
            "success": true,
            "execution": {
                "id": 789,
                "proc_run_id": 456,
                "pipe_name": "aretomo3",
                "status": "running",
                "job_id": "123456",
                "submitted_at": "2024-11-10T10:30:00Z",
                "started_at": "2024-11-10T10:31:00Z",
                "completed_at": null,
                "error_message": null,
                "parameters": {...}
            }
        }
    """
    try:
        try:
            execution = PipeExecution.objects.select_related(
                "proc_run",
                "pipe_in_plan",
                "pipe_in_plan__pipe",
            ).get(id=execution_id)
        except PipeExecution.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"PipeExecution with id {execution_id} not found",
                },
                status=404,
            )

        # Build response
        return JsonResponse(
            {
                "success": True,
                "execution": {
                    "id": execution.id,
                    "proc_run_id": execution.proc_run.id,
                    "proc_run_name": execution.proc_run.name,
                    "pipe_in_plan_id": execution.pipe_in_plan.id,
                    "pipe_name": execution.pipe_in_plan.pipe.name,
                    "software_name": execution.pipe_in_plan.pipe.software.name,
                    "status": execution.status,
                    "job_id": execution.job_id,
                    "script_path": execution.script_path,
                    "script_content": execution.script_content,
                    "submitted_at": execution.submitted_at.isoformat() if execution.submitted_at else None,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "error_message": execution.error_message,
                    "parameters": execution.parameters,
                    "created_at": execution.created_at.isoformat(),
                    "updated_at": execution.updated_at.isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting execution status: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def list_run_executions(request, proc_run_id: int):
    """
    List all pipe executions for a processing run.

    GET /workflow/v1/execution/run/<proc_run_id>/

    Returns:
        {
            "success": true,
            "proc_run": {
                "id": 456,
                "name": "run001",
                ...
            },
            "executions": [
                {
                    "id": 789,
                    "pipe_name": "aretomo3",
                    "status": "completed",
                    ...
                },
                ...
            ]
        }
    """
    try:
        try:
            proc_run = ProcRun.objects.get(id=proc_run_id)
        except ProcRun.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"ProcRun with id {proc_run_id} not found",
                },
                status=404,
            )

        # Get all executions for this run
        executions = (
            PipeExecution.objects.filter(
                proc_run=proc_run,
            )
            .select_related(
                "pipe_in_plan",
                "pipe_in_plan__pipe",
                "pipe_in_plan__pipe__software",
            )
            .order_by("pipe_in_plan__step")
        )

        execution_list = []
        for execution in executions:
            execution_list.append(
                {
                    "id": execution.id,
                    "pipe_in_plan_id": execution.pipe_in_plan.id,
                    "pipe_name": execution.pipe_in_plan.pipe.name,
                    "software_name": execution.pipe_in_plan.pipe.software.name,
                    "step": execution.pipe_in_plan.step,
                    "status": execution.status,
                    "job_id": execution.job_id,
                    "submitted_at": execution.submitted_at.isoformat() if execution.submitted_at else None,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "error_message": execution.error_message,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "proc_run": {
                    "id": proc_run.id,
                    "name": proc_run.name,
                    "proc_plan_name": proc_run.proc_plan.name,
                    "msi_session_name": proc_run.msi_session.name,
                },
                "executions": execution_list,
            }
        )

    except Exception as e:
        logger.error(f"Error listing run executions: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def check_dependencies(request):
    """
    Check if dependencies are met for executing a pipe.

    GET /workflow/v1/execution/check_dependencies/?pipe_in_plan_id=<id>&proc_run_id=<id>

    Returns:
        {
            "success": true,
            "dependencies_met": true,
            "missing_dependencies": [],
            "has_dependencies": false  # No dependencies to check
        }

        OR

        {
            "success": true,
            "dependencies_met": false,
            "missing_dependencies": [
                "ctf from motioncor2 (not completed)",
                ...
            ],
            "has_dependencies": true  # Has dependencies but not all met
        }
    """
    try:
        # Get query parameters
        pipe_in_plan_id = request.GET.get("pipe_in_plan_id")
        proc_run_id = request.GET.get("proc_run_id")

        if not pipe_in_plan_id or not proc_run_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Both pipe_in_plan_id and proc_run_id query parameters are required",
                },
                status=400,
            )

        try:
            pipe_in_plan_id = int(pipe_in_plan_id)
        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "pipe_in_plan_id must be an integer",
                },
                status=400,
            )

        try:
            proc_run_id = int(proc_run_id)
        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "proc_run_id must be an integer",
                },
                status=400,
            )

        try:
            pipe_in_plan = PipeInPlan.objects.get(id=pipe_in_plan_id)
        except PipeInPlan.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"PipeInPlan with id {pipe_in_plan_id} not found",
                },
                status=404,
            )

        try:
            proc_run = ProcRun.objects.get(id=proc_run_id)
        except ProcRun.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"ProcRun with id {proc_run_id} not found",
                },
                status=404,
            )

        # Check dependencies
        executor = PipelineExecutor()
        dependencies_met, missing = executor.check_dependencies_met(proc_run, pipe_in_plan)

        # Check if there are any dependencies to check
        from processes.models import PipeJoint

        has_dependencies = PipeJoint.objects.filter(pipe_in_plan=pipe_in_plan).exists()

        return JsonResponse(
            {
                "success": True,
                "dependencies_met": dependencies_met,
                "missing_dependencies": missing,
                "has_dependencies": has_dependencies,
            }
        )

    except Exception as e:
        logger.error(f"Error checking dependencies: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def lookup_execution_ids(request):
    """
    Look up pipe_in_plan_id and proc_run_id from user-friendly identifiers.

    GET /workflow/v1/execution/lookup_ids/?session_name=<name>&run_name=<name>&processor_name=<name>

    Query Parameters:
        session_name: MSI session name (e.g., "Grid6_2025-04-22")
        run_name: Processing run name (e.g., "run001")
        processor_name: Processor name (e.g., "aretomo3")

    Returns:
        {
            "success": true,
            "pipe_in_plan_id": 123,
            "proc_run_id": 456,
            "session_id": 789,
            "pipe_name": "aretomo3_basic"
        }

        OR (if not found):

        {
            "success": false,
            "error": "Session 'Grid6_2025-04-22' not found"
        }
    """
    try:
        # Get query parameters
        session_name = request.GET.get("session_name")
        run_name = request.GET.get("run_name")
        processor_name = request.GET.get("processor_name")

        # Validate required parameters
        if not session_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "session_name query parameter is required",
                },
                status=400,
            )

        if not run_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "run_name query parameter is required",
                },
                status=400,
            )

        if not processor_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "processor_name query parameter is required",
                },
                status=400,
            )

        # Look up MSI session
        try:
            msi_session = MsiSession.objects.get(name=session_name)
        except MsiSession.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Session '{session_name}' not found",
                },
                status=404,
            )

        # Get or create processing run
        # First, need to determine the right plan based on the processor
        try:
            # Get the processor to validate it exists
            processor = get_processor(processor_name)

            # Find which plan contains a pipe with this processor
            # Look through all PipeInPlans to find one with matching processor_class
            pipe_in_plan_with_processor = (
                PipeInPlan.objects.filter(
                    pipe__software__processor_class=processor_name,
                )
                .select_related("plan", "pipe", "pipe__software")
                .first()
            )

            if not pipe_in_plan_with_processor:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"No processing plan found with processor '{processor_name}'. "
                        f"Please create a plan with this processor first.",
                    },
                    status=404,
                )

            proc_plan = pipe_in_plan_with_processor.plan

        except ValueError as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Invalid processor '{processor_name}': {str(e)}",
                },
                status=404,
            )

        # Look up the processing run (do NOT create it - lookup should be read-only)
        try:
            proc_run = ProcRun.objects.get(
                msi_session=msi_session,
                name=run_name,
                proc_plan=proc_plan,
            )
        except ProcRun.DoesNotExist:
            # Run doesn't exist yet - this is okay for new runs
            # Return a special response indicating the run needs to be created
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Run '{run_name}' does not exist yet for session '{session_name}'. It will be created when you submit the job.",
                    "run_not_found": True,
                    "session_id": msi_session.id,
                },
                status=204,
            )

        # Look up pipe in plan that matches the processor
        # Find the pipe_in_plan where the pipe's software processor matches the requested processor
        pipe_in_plans = PipeInPlan.objects.filter(
            plan=proc_run.proc_plan,
        ).select_related("pipe", "pipe__software")

        matching_pipe_in_plan = None
        for pip in pipe_in_plans:
            # Check if this pipe's software processor class matches
            software = pip.pipe.software
            if hasattr(software, "processor_class") and software.processor_class == processor_name:
                matching_pipe_in_plan = pip
                break

        if not matching_pipe_in_plan:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        f"No pipeline step found for processor '{processor_name}' "
                        f"in processing plan '{proc_run.proc_plan.name}'"
                    ),
                },
                status=404,
            )

        # Return the IDs
        return JsonResponse(
            {
                "success": True,
                "pipe_in_plan_id": matching_pipe_in_plan.id,
                "proc_run_id": proc_run.id,
                "session_id": msi_session.id,
                "pipe_name": matching_pipe_in_plan.pipe.name,
                "software_name": matching_pipe_in_plan.pipe.software.name,
            }
        )

    except Exception as e:
        logger.error(f"Error looking up execution IDs: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def get_execution_by_job_id(request, job_id: str):
    """
    Get pipe execution data by SLURM job ID.

    GET /workflow/v1/execution/by_job_id/<job_id>/

    Returns:
        {
            "success": true,
            "execution": {
                "id": 789,
                "proc_run_id": 456,
                "proc_run_name": "run001",
                "pipe_name": "aretomo3_basic",
                "software_name": "aretomo3",
                "status": "running",
                "job_id": "123456",
                "script_path": "/path/to/script.sh",
                "submitted_at": "2024-11-10T10:30:00Z",
                "started_at": "2024-11-10T10:31:00Z",
                "completed_at": null,
                "error_message": null,
                "parameters": {...},
                "created_at": "2024-11-10T10:30:00Z",
                "updated_at": "2024-11-10T10:31:00Z"
            }
        }

        OR (if not found):

        {
            "success": false,
            "error": "No execution found for job_id '123456'"
        }
    """
    try:
        # Handle SLURM hetjob format (e.g., "9232+0" -> base job "9232")
        # Try exact match first, then base job ID without hetjob suffix
        base_job_id = job_id.split("+")[0] if "+" in job_id else job_id

        try:
            execution = PipeExecution.objects.select_related(
                "proc_run",
                "proc_run__msi_session",
                "proc_run__proc_plan",
                "pipe_in_plan",
                "pipe_in_plan__pipe",
                "pipe_in_plan__pipe__software",
            ).get(job_id=job_id)
        except PipeExecution.DoesNotExist:
            # Try base job ID if hetjob format was provided
            if base_job_id != job_id:
                try:
                    execution = PipeExecution.objects.select_related(
                        "proc_run",
                        "proc_run__msi_session",
                        "proc_run__proc_plan",
                        "pipe_in_plan",
                        "pipe_in_plan__pipe",
                        "pipe_in_plan__pipe__software",
                    ).get(job_id=base_job_id)
                except PipeExecution.DoesNotExist:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"No execution found for job_id '{job_id}' or '{base_job_id}'",
                        },
                        status=404,
                    )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"No execution found for job_id '{job_id}'",
                    },
                    status=404,
                )

        # On-demand log fetching for completed jobs that don't have logs yet
        if execution.status == "completed" and execution.logs_fetched_at is None:
            from workflow.log_fetcher import fetch_job_logs

            logger.info(f"Fetching logs on-demand for job {job_id}")
            try:
                fetch_job_logs(execution)
                # Refresh from database to get updated logs
                execution.refresh_from_db()
            except Exception as e:
                logger.error(f"Error fetching logs on-demand for job {job_id}: {e}")
                # Continue anyway - we'll return what we have

        # Build response
        return JsonResponse(
            {
                "success": True,
                "execution": {
                    "id": execution.id,
                    "proc_run_id": execution.proc_run.id,
                    "proc_run_name": execution.proc_run.name,
                    "msi_session_name": execution.proc_run.msi_session.name,
                    "proc_plan_name": execution.proc_run.proc_plan.name,
                    "pipe_in_plan_id": execution.pipe_in_plan.id,
                    "pipe_name": execution.pipe_in_plan.pipe.name,
                    "software_name": execution.pipe_in_plan.pipe.software.name,
                    "status": execution.status,
                    "job_id": execution.job_id,
                    "script_path": execution.script_path,
                    "script_content": execution.script_content,
                    "submitted_at": execution.submitted_at.isoformat() if execution.submitted_at else None,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "error_message": execution.error_message,
                    "parameters": execution.parameters,
                    "created_at": execution.created_at.isoformat(),
                    "updated_at": execution.updated_at.isoformat(),
                    # Job logs (stdout/stderr from SLURM)
                    "stdout_log": execution.stdout_log,
                    "stderr_log": execution.stderr_log,
                    "logs_fetched_at": execution.logs_fetched_at.isoformat() if execution.logs_fetched_at else None,
                    "log_fetch_error": execution.log_fetch_error,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting execution by job_id: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# Processor-Specific Custom Endpoints


@require_http_methods(["GET"])
@login_required
def get_processor_options(request, processor_name: str):
    """
    Get dynamic form field options for a specific processor.

    GET /workflow/v1/processors/<name>/options/
    GET /workflow/v1/processors/<name>/options/?session_id=<id>

    Delegates to processor-specific views module if available.

    Returns:
        {
            "success": true,
            "options": {
                "field_name": [
                    {"value": "...", "label": "...", "description": "..."},
                    ...
                ],
                ...
            }
        }
    """
    try:
        processor = get_processor(processor_name)
        session_id = request.GET.get("session_id")

        # Check if processor has custom views module
        if processor.has_custom_views():
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, "get_dynamic_options"):
                # Delegate to processor-specific implementation
                return views_module.get_dynamic_options(request, session_id)

        # Default: return empty options
        return JsonResponse(
            {
                "success": True,
                "options": {},
            }
        )

    except ValueError as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=404,
        )

    except Exception as e:
        logger.error(f"Error getting processor options: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def validate_processor_parameters(request, processor_name: str):
    """
    Validate processor parameters before submission.

    POST /workflow/v1/processors/<name>/validate/
    Body: {"param1": value1, "param2": value2, ...}

    Delegates to processor-specific views module if available.

    Returns:
        {
            "valid": true/false,
            "errors": [
                {"field": "param_name", "message": "Error description"},
                ...
            ]
        }
    """
    try:
        processor = get_processor(processor_name)

        # Check if processor has custom views module
        if processor.has_custom_views():
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, "validate_parameters"):
                # Delegate to processor-specific implementation
                return views_module.validate_parameters(request)

        # Default: return valid (assumes JSON Schema validation is enough)
        return JsonResponse(
            {
                "valid": True,
                "errors": [],
            }
        )

    except ValueError as e:
        return JsonResponse(
            {
                "valid": False,
                "errors": [{"field": "__all__", "message": str(e)}],
            },
            status=404,
        )

    except Exception as e:
        logger.error(f"Error validating processor parameters: {e}", exc_info=True)
        return JsonResponse(
            {
                "valid": False,
                "errors": [{"field": "__all__", "message": str(e)}],
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def get_processor_defaults(request, processor_name: str):
    """
    Get session-specific default parameters for a processor.

    GET /workflow/v1/processors/<name>/defaults/
    GET /workflow/v1/processors/<name>/defaults/?session_id=<id>

    Delegates to processor-specific views module if available.

    Returns:
        {
            "success": true,
            "defaults": {
                "param1": value1,
                "param2": value2,
                ...
            }
        }
    """
    try:
        processor = get_processor(processor_name)
        session_id = request.GET.get("session_id")

        # Check if processor has custom views module
        if processor.has_custom_views():
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, "get_session_defaults"):
                # Delegate to processor-specific implementation
                return views_module.get_session_defaults(request, session_id)

        # Default: return empty defaults
        return JsonResponse(
            {
                "success": True,
                "session_info": {},
                "defaults": {},
            }
        )

    except ValueError as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=404,
        )

    except Exception as e:
        logger.error(f"Error getting processor defaults: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def get_processor_metadata(request, processor_name: str):
    """
    Get processor metadata for UI display.

    GET /workflow/v1/processors/<name>/metadata/

    Provides help text, examples, documentation links, and parameter notes.
    Delegates to processor-specific views module if available.

    Returns:
        {
            "success": true,
            "metadata": {
                "help_text": "Description...",
                "category": "Pre-processing",
                "examples": [{"title": "...", "params": {...}}, ...],
                "docs_url": "https://...",
                "parameter_notes": {"param1": "Note about param1", ...}
            }
        }
    """
    try:
        processor = get_processor(processor_name)

        # Check if processor has custom views module
        if processor.has_custom_views():
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, "get_processor_metadata"):
                # Delegate to processor-specific implementation
                return views_module.get_processor_metadata(request)

        # Default: return basic metadata from processor class
        return JsonResponse(
            {
                "success": True,
                "metadata": {
                    "help_text": f"{processor.display_name} processor",
                    "category": "Processing",
                    "examples": [],
                    "docs_url": None,
                    "parameter_notes": {},
                },
            }
        )

    except ValueError as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=404,
        )

    except Exception as e:
        logger.error(f"Error getting processor metadata: {e}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@require_http_methods(["GET"])
@login_required
def validate_processor_session(request, processor_name: str):
    """
    Run processor-specific session validation (e.g., MDOC magnification check).

    GET /workflow/v1/processors/<name>/validate-session/?session_id=<id>

    Delegates to processor-specific views module if available.
    This is separated from defaults to avoid blocking form loading with slow I/O.
    """
    try:
        processor = get_processor(processor_name)
        session_id = request.GET.get("session_id")

        if processor.has_custom_views():
            views_module = processor.get_views_module()
            if views_module and hasattr(views_module, "validate_session"):
                return views_module.validate_session(request, session_id)

        return JsonResponse({"success": True, "validation": {}})

    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)

    except Exception as e:
        logger.error(f"Error validating processor session: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@extend_schema(
    methods=["GET"],
    description="""Returns MSI sessions and associated run numbers for a given processing plan type.

Used to determine the next available run number when submitting jobs.

**Supported plan types:**
- `aretomo3` → czii-live plan (default)
- `denoise` → czii-denoise plan
- `copick` → czii-copick plan (create project)
- `copick-add-object` → copick-add-object plan (add pickable objects)
- `copick-import` → copick-import plan (import tomograms)
- `membraneseg` → membraneseg plan (membrane segmentation)
- `octopi` → czii-octopi plan

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
            description="Processing plan type. Defaults to 'aretomo3'.",
            enum=["aretomo3", "denoiset", "copick", "copick-add-object", "copick-import", "membraneseg", "octopi"],
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
def get_plan_runs(request):
    """Get MSI sessions with their run numbers for a given processing plan type."""
    try:
        session_name_filter = request.GET.get("session_name", None)
        plan_type = request.GET.get("plan_type", "aretomo3")

        # Map plan_type → ProcPlan.name
        plan_map = {
            "aretomo3": "czii-live",
            "denoiset": "czii-denoise",
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

        try:
            plan = ProcPlan.objects.get(name=plan_name)
            plan_id = plan.id
            logger.info(f"Found plan {plan_name} with ID: {plan_id}")
        except ProcPlan.DoesNotExist:
            logger.error(f"Processing plan {plan_name} not found")
            return JsonResponse({"error": f"Processing plan {plan_name} not found"}, status=404)

        query = (
            MsiSession.objects.filter(procrun__proc_plan_id=plan_id)
            .annotate(
                run_number=F("procrun__name"),
                run_created_at=F("procrun__created_at"),
            )
            .values("name", "run_number", "run_created_at")
            .distinct()
        )

        if session_name_filter:
            query = query.filter(name=session_name_filter)

        query_results = list(query)

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
