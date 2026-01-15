"""
Run-related view functions for processing workflows.

This module contains views for creating, reserving, and managing processing runs.
"""
import json

from django.contrib.auth.decorators import login_required
from django.forms import ModelChoiceField
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view
from tem.models import MsiSession

from processes.models import Annotation, ProcPlan, ProcRun, RunPipeData, Tomograms, suggest_name

from ..forms import ReserveFrameProcRunForm, ReserveTomoProcRunForm, UpdateNotesForm


def detail(request, run_id):
    run = get_object_or_404(ProcRun, pk=run_id)
    if request.method == 'POST':
        new_notes=request.POST['notes']
        run.notes = new_notes
        run.save()
    field_objs = run._meta.get_fields()
    fields = {}
    for f in field_objs:
        try:
            fields[f.name] = getattr(run, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        except TypeError:
            print(f)
            continue
        #ManyToManyField
        if hasattr(fields[f.name],'all'):
            fields[f.name] = list(map((lambda x: x.__str__()),fields[f.name].all()))
    all_pipe_data = RunPipeData.objects.filter(run=run)
    form = UpdateNotesForm(instance=run)
    context = {
            "data": run,
            "fields": fields,
            "pipe_data": all_pipe_data,
            "paths": {
                    "update_notes": form,
            },
    }
    return render(request, "processes/detail.html", context)


@login_required
def reserve_run(request):
    if request.method == 'POST':
        form = ReserveFrameProcRunForm(request.POST)
        return render(request, reverse("processes:create"))
    else:
        form = ReserveFrameProcRunForm()
        return render(request, "processes/reserve.html", {"form": form})


@extend_schema(
    methods=["POST"],
    description="Creates a new ProcRun given a processing plan and MSI session. Returns a redirect to the run's detail page.",
    request={
        "type": "object",
        "properties": {
            "proc_plan": {"type": "integer", "description": "ID of the processing plan"},
            "msi_session": {"type": "integer", "description": "ID of the MSI session"},
        },
        "required": ["proc_plan", "msi_session"],
    },
    responses={
        302: OpenApiTypes.STR,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
        405: OpenApiTypes.OBJECT,
    },
)
@csrf_exempt
@api_view(["POST"])
@require_http_methods(["POST"])
def create_run(request):
    if request.method == 'POST':
        try:
            data = request.data #json.loads(request.body.decode('utf-8'))  # Parse JSON data
            plan_id = int(data.get('proc_plan'))  # Extract `proc_plan`
            session_id = int(data.get('msi_session'))  # Extract `msi_session`
            run_number = data.get('run_number')  # Extract the actual run number specified by user

            msi_session = MsiSession.objects.get(pk=session_id)
            proc_plan = ProcPlan.objects.get(pk=plan_id)

            # Use the specified run number if provided, otherwise generate one
            if run_number:
                # Ensure the run number has the correct format (e.g., "run001")
                if not run_number.startswith('run'):
                    run_number = f"run{run_number.zfill(3)}"
                name = run_number

                # Check if this run number already exists for this session and plan
                existing_run = ProcRun.objects.filter(
                    name=name,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
                ).first()

                if existing_run:
                    return JsonResponse(
                        {'error': f'Run {name} already exists for this session and plan.'},
                        status=409,
                    )
            else:
                # Generate a name using suggest_name if run_number not specified
                from processes.models import suggest_name
                name = suggest_name(proc_plan, msi_session)

            # Create the ProcRun instance
            run_instance = ProcRun.objects.create(
                name=name,
                msi_session=msi_session,
                proc_plan=proc_plan,
            )

            # Return the detail URL as a 302 redirect
            return HttpResponseRedirect(reverse('processes:detail', args=(run_instance.id,)))
        except (ProcPlan.DoesNotExist, MsiSession.DoesNotExist) as e:
            return JsonResponse({'error': f'Invalid proc_plan or msi_session: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)


@extend_schema(
    methods=["POST"],
    summary="Check if a run number is available (pre-flight)",
    description=(
        "Validates that a given run number is available for a specific processing plan and session. "
        "Does **not** create any database records—this is purely a reservation check. "
        "Normalizes run_number to `run###` format if needed."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "proc_plan": {"type": "integer", "example": 12, "description": "Processing plan ID"},
                "msi_session": {"type": "integer", "example": 45, "description": "MSI session ID"},
                "run_number": {
                    "type": "string",
                    "example": "002",
                    "description": "Run number to check (e.g., '002', 'run003', etc.)",
                },
            },
            "required": ["proc_plan", "msi_session", "run_number"],
        },
    },
    responses={
        200: OpenApiResponse(
            description="Reservation is available",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Available",
                    value={
                        "message": "Reservation available.",
                        "proc_plan": 12,
                        "msi_session": 45,
                        "run_number": "run002",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad request – missing or invalid parameters",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Missing run_number",
                    value={"error": "run_number is required"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Invalid payload",
                    value={"error": "Invalid payload"},
                    response_only=True,
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Plan or session not found",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Plan not found",
                    value={"error": "Invalid proc_plan"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Session not found",
                    value={"error": "Invalid msi_session"},
                    response_only=True,
                ),
            ],
        ),
        409: OpenApiResponse(
            description="Conflict – run already exists for this plan and session.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Already exists",
                    value={"error": "Run run002 already exists for this session and plan."},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Unhandled server error.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Server error",
                    value={"error": "Unexpected error: 500"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["processes"],
)
@csrf_exempt
@api_view(["POST"])
@require_http_methods(["POST"])
def reserve_generic_run(request):
    try:
        data = request.data # json.loads(request.body.decode("utf-8"))
        plan_id = int(data.get("proc_plan"))
        session_id = int(data.get("msi_session"))
        run_number = (data.get("run_number") or "").strip()

        if not run_number:
            return JsonResponse({'error': 'run_number is required'}, status=400)

        # normalize like create_run (allow raw "002")
        if not run_number.startswith('run'):
            run_number = f"run{run_number.zfill(3)}"

        proc_plan = ProcPlan.objects.get(pk=plan_id)
        msi_session = MsiSession.objects.get(pk=session_id)

        exists = ProcRun.objects.filter(
            name=run_number, proc_plan=proc_plan, msi_session=msi_session,
        ).exists()
        if exists:
            return JsonResponse(
                {'error': f'Run {run_number} already exists for this session and plan.'},
                status=409,
            )

        # No DB write here—just confirming availability
        return JsonResponse({
            'message': 'Reservation available.',
            'proc_plan': proc_plan.id,
            'msi_session': msi_session.id,
            'run_number': run_number,
        }, status=200)

    except ProcPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid proc_plan'}, status=404)
    except MsiSession.DoesNotExist:
        return JsonResponse({'error': 'Invalid msi_session'}, status=404)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@extend_schema(
    methods=["POST"],
    summary="Create a generic ProcRun (no tomograms)",
    description=(
        "Creates a minimal `ProcRun` linked to a given processing plan and microscopy session. "
        "Normalizes `run_number` to the `run###` format if needed. "
        "Does **not** attach tomograms or pipeline data; stores optional `notes` or a default note (`pipeline=<pipeline>`)."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "proc_plan": {
                    "type": "integer",
                    "example": 12,
                    "description": "Primary key of `ProcPlan`.",
                },
                "msi_session": {
                    "type": "integer",
                    "example": 45,
                    "description": "Primary key of `MsiSession`.",
                },
                "run_number": {
                    "type": "string",
                    "example": "002",
                    "description": "Run number (e.g., '002', 'run003'). Will be normalized to 'run###'.",
                },
                "pipeline": {
                    "type": "string",
                    "example": "copick",
                    "description": "Optional pipeline name (defaults to 'generic').",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes for the run. Defaults to 'pipeline=<pipeline>' if empty.",
                },
            },
            "required": ["proc_plan", "msi_session", "run_number"],
        },
    },
    responses={
        201: OpenApiResponse(
            description="Run created successfully",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "message": "Generic run created (no tomograms).",
                        "run_id": 789,
                        "run_number": "run002",
                        "session_id": 45,
                        "plan_id": 12,
                        "detail_url": "/processes/789/",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad request – missing or invalid parameters",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Missing run_number",
                    value={"error": "run_number is required"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Invalid integers",
                    value={"error": "proc_plan and msi_session must be integers"},
                    response_only=True,
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Plan or session not found",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Plan not found",
                    value={"error": "Invalid proc_plan"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Session not found",
                    value={"error": "Invalid msi_session"},
                    response_only=True,
                ),
            ],
        ),
        409: OpenApiResponse(
            description="Conflict – run already exists",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Duplicate",
                    value={"error": "Run run002 already exists for this session and plan."},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Unhandled server error",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample("Server error", value={"error": "Unexpected error details"}, response_only=True),
            ],
        ),
    },
    tags=["processes"],
)
@csrf_exempt
@api_view(["POST"])
@require_http_methods(["POST"])
def create_generic_run(request):
    """
    Create a lightweight ProcRun (no input tomograms, no pipe data).
    Required JSON: proc_plan, msi_session, run_number
    Optional JSON: pipeline (e.g., "copick"), notes
    """
    try:
        data = request.data # json.loads(request.body.decode('utf-8'))

        # Validate inputs
        try:
            plan_id = int(data.get('proc_plan'))
            session_id = int(data.get('msi_session'))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'proc_plan and msi_session must be integers'}, status=400)

        run_number = (data.get('run_number') or '').strip()
        pipeline = (data.get('pipeline') or 'generic').strip()
        notes = data.get('notes') or ''

        if not run_number:
            return JsonResponse({'error': 'run_number is required'}, status=400)

        # Normalize: run### format
        if not run_number.startswith('run'):
            run_number = f"run{run_number.zfill(3)}"
        name = run_number

        msi_session = MsiSession.objects.get(pk=session_id)
        proc_plan = ProcPlan.objects.get(pk=plan_id)

        # Uniqueness guard
        if ProcRun.objects.filter(name=name, msi_session=msi_session, proc_plan=proc_plan).exists():
            return JsonResponse({'error': f'Run {name} already exists for this session and plan.'}, status=409)

        run_instance = ProcRun.objects.create(
            name=name,
            msi_session=msi_session,
            proc_plan=proc_plan,
            notes=notes or f'pipeline={pipeline}',
        )

        return JsonResponse({
            'message': 'Generic run created (no tomograms).',
            'run_id': run_instance.id,
            'run_number': run_instance.name,
            'session_id': msi_session.id,
            'plan_id': proc_plan.id,
            'detail_url': reverse('processes:detail', args=(run_instance.id,)),
        }, status=201)

    except ProcPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid proc_plan'}, status=404)
    except MsiSession.DoesNotExist:
        return JsonResponse({'error': 'Invalid msi_session'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# POST-TOMOGRAM PROCESSING VIEWS
# Legacy views for post-tomogram processing runs (integrated from views_post_tomo.py)
# ============================================================================

def detail_post_tomo(request, run_id):
    """Legacy template view for post-tomogram run details"""
    run = get_object_or_404(ProcRun, pk=run_id)
    if request.method == 'POST':
        new_notes=request.POST['notes']
        run.notes = new_notes
        run.save()
    field_objs = run._meta.get_fields()
    fields = {}
    for f in field_objs:
        try:
            fields[f.name] = getattr(run, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        except TypeError:
            print(f)
            continue
        #ManyToManyField
        if hasattr(fields[f.name],'all'):
            fields[f.name] = list(map((lambda x: x.__str__()),fields[f.name].all()))
    all_pipe_data = RunPipeData.objects.filter(run=run)
    form = UpdateNotesForm(instance=run)
    context = {
            "data": run,
            "fields": fields,
            "pipe_data": all_pipe_data,
            "paths": {
                    "update_notes": form,
            },
    }
    return render(request, "processes/ptdetail.html", context)

def reserve_run_post_tomo(request):
    """Legacy template view for reserving a post-tomogram processing run"""
    print('Reserving')
    if request.method == 'POST':
        print('Post-----')
        form = ReserveTomoProcRunForm(request.POST)
        print(request.POST)
        if ('input_tomo' not in request.POST.keys() or not request.POST['input_tomo']) and 'msi_session' in request.POST.keys():
            session_id=int(request.POST['msi_session'])
            msi_session=MsiSession.objects.get(pk=session_id)
            input_tomo = ModelChoiceField(queryset=Tomograms.objects.filter(msi_session=msi_session))
            return render(request, "processes/ptselect.html", {"form": form, "input_tomo_field": input_tomo})
        else:
            print('reserve success', request.POST)
            return render(request, reverse("processes:ptselect"))
    else:
        form = ReserveTomoProcRunForm()
        input_tomo = ModelChoiceField(queryset=Tomograms.objects.all())
        return render(request, "processes/ptreserve.html", {"form": form, "input_tomo_field": input_tomo })

def create_run_post_tomo(request):
    """Legacy template view for creating a post-tomogram processing run"""
    if request.method == 'POST':
        plan_id=int(request.POST['proc_plan'])
        session_id=int(request.POST['msi_session'])
        input_tomo_id=int(request.POST['input_tomo'])
        input_tomo=Tomograms.objects.get(pk=input_tomo_id)
        input_objects = {'tomo':input_tomo}
        if 'input_pick' in request.POST.keys():
            input_pick_id=int(request.POST['input_pick'])
            input_pick=Annotation.objects.get(pk=input_pick_id)
            input_objects['pick']=input_pick
        else:
            input_pick_id = False
            input_objects['pick']=False
        msi_session=MsiSession.objects.get(pk=session_id)
        proc_plan=ProcPlan.objects.get(pk=plan_id)

        # Use the specified run number if provided, otherwise generate one
        run_number = request.POST.get('run_number')
        if run_number:
            # Ensure the run number has the correct format (e.g., "run001")
            if not run_number.startswith('run'):
                run_number = f"run{run_number.zfill(3)}"
            name = run_number

            # Check if this run number already exists for this session and plan
            existing_run = ProcRun.objects.filter(
                name=name,
                msi_session=msi_session,
                proc_plan=proc_plan,
            ).first()

            if existing_run:
                return JsonResponse({
                    'error': f'Run number {name} already exists for this session and plan. Please choose a different run number.',
                }, status=400)
        else:
            # Fallback to the old behavior if no run number is specified
            name = suggest_name('run',msi_session,proc_plan)
        run_instance = ProcRun.objects.create(
                    name=name,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
        )
        run_instance.save()
        run_instance.save_pipe_run_data()
        run_instance.create_tomogram_collection(input_objects)
        return HttpResponseRedirect(reverse('processes:ptdetail', args=(run_instance.id,)))
