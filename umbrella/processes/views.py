from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProcRunForm, ReserveFrameProcRunForm, UpdateNotesForm
from django.contrib.auth.decorators import login_required
from . import models
from processes.models import ProcRun, ProcPlan, ProcSoftware, RunPipeData
from tem.models import MsiSession
from django.core.serializers import serialize
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from django.db.models.functions import Substr, StrIndex, Trim
from pydantic import ValidationError
from django.utils.timezone import now
from datetime import timedelta
from datetime import datetime
from tem.models import MsiSession
from django.db.models import Case, When, F, Value, CharField, Count
from cryo_grids.models import CryoGrid, PlungeFreezingSession, PlungeFreezingPlan
from processes.models import *
from processes.utils import QueryParams
from tem.models import MsiSession
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
            }
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
@login_required
def create_run(request):
    plan_id=int(request.POST['proc_plan'])
    session_id=int(request.POST['msi_session'])
    msi_session=MsiSession.objects.get(pk=session_id)
    proc_plan=ProcPlan.objects.get(pk=plan_id)
    name = suggest_name('run',msi_session,proc_plan)

    if request.method == 'POST':
        run_instance = ProcRun.objects.create(
                    name=name,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
        )
        run_instance.save()
        my_pk = run_instance.id
        path_dicts = {}
        run_instance.save()
        run_instance.save_pipe_run_data()
        run_instance.create_tomogram_collection()
        return HttpResponseRedirect(reverse('processes:detail', args=(run_instance.id,)))

@require_http_methods(["GET"])
def get_all_runs(request):
    if not request.GET.get('valid', 'true') == 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    run_list = Session.objects.all()
    serialized_runs = serialize('json', run_list)
    run_data = json.loads(serialized_runs)
    return JsonResponse(run_data, safe=False)

@require_http_methods(["GET"])
def get_all_image_paths(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    name_param = request.GET.get('name')

    software_query = ProcSoftware.objects.select_related(
        'frames', 'sums', 'mdocs', 'parents', 'atlas'
    ).all()

    result_list: List[dict] = []
    for software in software_query:
        software_data = ProcSoftwareResponseModel(
            model="tem.software",
            pk=software.pk,
            fields=ProcSoftwareFieldsResponse(
                name=software.name,
                frames=PathInfo(
                    static_path=software.frames.static_path if software.frames else None,
                    overlay_path=software.frames.overlay_path if software.frames else None,
                ),
                sums=PathInfo(
                    static_path=software.sums.static_path if software.sums else None,
                    overlay_path=software.sums.overlay_path if software.sums else None,
                ),
                mdocs=PathInfo(
                    static_path=software.mdocs.static_path if software.mdocs else None,
                    overlay_path=software.mdocs.overlay_path if software.mdocs else None,
                ),
                parents=PathInfo(
                    static_path=software.parents.static_path if software.parents else None,
                    overlay_path=software.parents.overlay_path if software.parents else None,
                ),
                atlas=PathInfo(
                    static_path=software.atlas.static_path if software.atlas else None,
                    overlay_path=software.atlas.overlay_path if software.atlas else None,
                )
            )
        )
        result_list.append(software_data.dict())

    if not name_param:
        return JsonResponse(content=result_list.dict())
    #case sensitive
    filtered_results = [item for item in result_list if item['fields']['name'].lower() == name_param.lower()]
    if filtered_results:
        return JsonResponse(data=filtered_results[0], safe=False)

    # Use ErrorResponse model correctly by converting it to a dictionary
    error_response = ErrorResponse(error='No matching software found')

    return JsonResponse(data=error_response.dict(), status=404, safe=False)



#for tomo filter page

@require_http_methods(["GET"])
def available_filters(request):
    try:
        # Validate that only the 'q' parameter is present in the request
        if 'q' not in request.GET or len(request.GET) > 1:
            return JsonResponse({'error': 'Invalid query parameters. Only "q" is allowed.'}, status=422)
        
        raw_query_param = request.GET.get('q', '[]')
        
        # Parse the JSON string into a Python list
        query_filters = json.loads(raw_query_param)

        # Validate the parsed list with Pydantic
        query_params = QueryParams(q=query_filters)

        # Initialize the selected filters based on the validated query parameters
        selected_filters = {}
        for qf in query_params.q:
            selected_filters[qf.category] = set(qf.value)  # Store as a set for efficient lookup

        # Base queryset with annotations for counting occurrences
        queryset = MsiSession.objects.select_related('project', 'user', 'msisession_name')
        sample_queryset = CryoGrid.objects.select_related('freezing_session','freezing_plan'
        ).prefetch_related(
            'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        )
        procplan_queryset = ProcPlan.objects.select_related('name')
        procrun_queryset = ProcRun.objects.select_related('created_at')
        current_time = now()
        date_ranges = {
            'last_1_month': current_time - timedelta(days=30),
            'last_3_months': current_time - timedelta(days=90),
            'last_6_months': current_time - timedelta(days=180),
        }

        # Helper function to add 'selected' key based on user selection
        def add_selected_status(filter_list, category):
            selected_values = selected_filters.get(category, set())
            if None in selected_values:
                for item in filter_list:
                    item['selected'] = item['name'] is None
            else:
                for item in filter_list:
                    item_name = item['name']
                    if isinstance(item_name, bool):
                        item['selected'] = item_name in selected_values
                    elif isinstance(item_name, str):
                        item['selected'] = item_name.strip().lower() in {val.lower() for val in selected_values if isinstance(val, str)}
                    else:
                        item['selected'] = False

        # Aggregating counts for each filter
        filters = {
            'project': list(queryset.annotate(project_temp_name=F('project__name'))
                            .values('project_temp_name')
                            .annotate(count=Count('id'))
                            .order_by('project_temp_name')
                            .values(name=F('project_temp_name'), count=F('count'))),
            'sample': list(sample_queryset.annotate(sample_temp_name=F('freezing_plan__sample__name'))
                        .values(sample_temp_name=F('sample_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('sample_temp_name')
                        .values(name=F('sample_temp_name'), count=F('count'))),
            'user': list(queryset.annotate(
                            user_display_name=Trim(
                                Case(
                                    # If username contains '@', take the substring before '@'
                                    When(user__username__contains='@',
                                         then=Substr(F('user__username'), 1, StrIndex(F('user__username'), Value('@')) - 1)),
                                    # Otherwise, use username or full name if available
                                    default=Case(
                                        When(user__first_name='', then=F('user__username')),
                                        default=F('user__first_name'),
                                        output_field=CharField()
                                    ),
                                    output_field=CharField()
                                )
                            )
                        ).values(user_display_name=F('user_display_name'))
                        .annotate(count=Count('id'))
                        .order_by('user_display_name')
                        .values(name=Trim(F('user_display_name')), count=F('count'))),
            'msiSession': list(queryset
                    .exclude(name__isnull=True) 
                    .annotate(count=Count('id'))
                    .values('name', 'count')
                    .order_by('name')),
            'screeningSession': list(sample_queryset
                         .filter(freezing_session__isnull=False, atlassession__group__name__isnull=False)
                         .annotate(screen_session_temp_name=F('atlassession__group__name'))
                         .values(screen_session_temp_name=F('screen_session_temp_name'))
                         .annotate(count=Count('id'))
                         .order_by('screen_session_temp_name')
                         .values(name=F('screen_session_temp_name'), count=F('count'))),
            'procPlan': list(procplan_queryset
                     .exclude(name__isnull=True)
                     .annotate(count=Count('id'))
                     .values('name', 'count')
                     .order_by('name')),
            'date': [
                {"name": "last_1_month", "count": procrun_queryset.filter(created_at__gte=date_ranges['last_1_month']).count()},
                {"name": "last_3_months", "count": procrun_queryset.filter(created_at__gte=date_ranges['last_3_months']).count()},
                {"name": "last_6_months", "count": procrun_queryset.filter(created_at__gte=date_ranges['last_6_months']).count()}
            ]
        }

        # Apply 'selected' status to filters
        for key, filter_list in filters.items():
            add_selected_status(filter_list, key)

        # Convert to the expected output format
        response_data = {
            "filters": filters
        }

        return JsonResponse(response_data)
    except ValidationError as e:
        # Handle Pydantic validation errors
        return JsonResponse({'error': f'Invalid input: {e.errors()}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)