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
from processes.utils import QueryParams, TomogramModel, tomoQueryParams, UnprocessableEntity, ResponseModel, ProcPlanModel, ProcRunModel,ProjectModel,JsonModel,GridModel,PaginationMetadataModel, UserModel,MSISessionModel
from tem.models import MsiSession
from django.db.models import F,Q

import logging
import os
# from umbrella.settings import ENVIRONMENT
logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')


def get_base_url():
       if ENVIRONMENT == 'staging':
           return 'http://umbrella-dev.czbiohub.org'
       elif ENVIRONMENT == 'production':
           return 'http://umbrella.czbiohub.org'
       else:  # development
           return 'http://localhost:8000'

base_url = get_base_url()

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


def get_freezing_plan_tags(fz_plan_id):
    try:
        freezing_plan = PlungeFreezingPlan.objects.get(id=fz_plan_id)
        freezing_plan_list = []
        for sample in freezing_plan.sample.all():
            tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
        return f"{sample.name} with {tag_names}" if tag_names else f"{sample.name} without tag"
    except Exception:
        return None

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


from django.http import JsonResponse
from pydantic import ValidationError
from typing import List
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

@require_http_methods(["GET"])
def get_tomo_details(request):
    try:
        # Parse 'q' parameter if provided
        raw_q_param = request.GET.get('q', None)
        if raw_q_param:
            try:
                q_param = json.loads(raw_q_param)
            except json.JSONDecodeError as e:
                return JsonResponse({'error': f'Invalid JSON format for q parameter: {str(e)}'}, status=400)
        else:
            q_param = []
        print(q_param)
        query_data = request.GET.dict()
        query_data['q'] = q_param

        # Validate query parameters
        try:
            query_params = tomoQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        # Pagination and sorting defaults
        page = int(request.GET.get('page', 1))  # Default to first page
        page_size = int(request.GET.get('pageSize', 20))  # Default page size is 10
        sort_field = 'created_at'
        asc = False

        # Helper function to extract values
        def extract_value(value):
            return value[0] if isinstance(value, list) and value else value

        # Override pagination and sorting if provided in q_param
        for item in q_param:
            if item['category'] == 'sort':
                # Map 'createdAt' to the actual database field for sorting
                sort_value = extract_value(item['value'])
                if sort_value == 'createdAt':
                    sort_field = 'created_at'  # Corresponding database field
                else:
                    sort_field = sort_value
            elif item['category'] == 'asc':
                asc_value = extract_value(item['value'])
                asc = bool(asc_value) if isinstance(asc_value, bool) else asc_value.lower() == 'true'
            elif item['category'] == 'page':
                page = int(extract_value(item['value']))
            elif item['category'] == 'pageSize':
                page_size = int(extract_value(item['value']))



        # Determine sort order
        sort_order = sort_field if asc else f'-{sort_field}'


        # Base queryset with selected related fields
        queryset = ProcRun.objects.select_related(
            'proc_plan',  # Direct relationship
            'msi_session',  # Join with tem_msisession
            'freezing_session',
            'msi_session__project',  # Join with the related project
            'msi_session__grid',  # Join with the related grid
            'msi_session__user',  # Join with the related user
            'msi_session__atlas_session',  # Join with tem_atlassession
            'msi_session__atlas_session__group',  # Join with tem_screensessiongroup
            'msi_session__grid__freezing_plan'  # Join with plungefreezingplan
        ).prefetch_related(
            'msi_session__grid__freezing_plan__sample',  # Prefetch the many-to-many relationship
            'runpipedata_set__tomograms_set'
        ).values(
            'id',
            'name',
            'notes',
            'created_at',
            'proc_plan_id',
            'msi_session_id',
            proc_plan_plan_id=F('proc_plan__id'),
            proc_plan_name=F('proc_plan__name'),
            run_pipe_run_id=F('runpipedata__run_id'),
            msi_session_name=F('msi_session__name'),
            msi_session_notes=F('msi_session__notes'),
            msi_session_project_id=F('msi_session__project_id'),
            msi_session_grid_id=F('msi_session__grid_id'),
            cryogrid_id=F('msi_session__grid__id'),
            cryogrid_name=F('msi_session__grid__name'),
            cryogrid_trashed=F('msi_session__grid__trashed'),
            cryogrid_created_at=F('msi_session__grid__updated_on'),
            project_id=F('msi_session__project__id'),
            project_name=F('msi_session__project__name'),
            user_id=F('msi_session__user__id'),
            user_name=F('msi_session__user__username'),
            fz_plan_id=F('msi_session__grid__freezing_plan__id'),
            screening_session_name=F('msi_session__atlas_session__group__name'),
            fz_plan_sample_id=F('msi_session__grid__freezing_plan__sample__id'),
            fz_plan_sample_name=F('msi_session__grid__freezing_plan__sample__name')
        ).order_by(sort_order)

        date_mapping = {
            'last_1_month': 1,
            'last_3_months': 3,
            'last_6_months': 6
        }

        filter_criteria = Q()

        for item in q_param:
            category = item['category']
            values = item['value']


            if category == 'procPlan':
                filter_criteria &= Q(proc_plan__name__in=values)
            elif category == 'userName':
                # Automatically detect email-like usernames (contains '@') or general usernames

                # Handle email-like usernames in the database
                user_filter = Q()
                for value in values:
                    # Use `startswith` to match both exact usernames and email-like formats
                    user_filter |= Q(msi_session__user__username__startswith=value)
                filter_criteria &= user_filter

            elif category == 'screeningSession':
                # Support multiple `icontains` values with OR logic
                session_filter = Q()
                for value in values:
                    session_filter |= Q(msi_session__atlas_session__group__name__icontains=value)
                filter_criteria &= session_filter
            elif category == 'grid':
                filter_criteria &= Q(msi_session__grid__name__in=values)
            elif category == 'project':
                filter_criteria &= Q(msi_session__project__name__in=values)
            elif category == 'msiSession':
                # Support multiple `icontains` values with OR logic
                session_name_filter = Q()
                for value in values:
                    session_name_filter |= Q(msi_session__name__icontains=value)
                filter_criteria &= session_name_filter
            elif category == 'tomograms':
                filter_criteria &= Q(name__in=values)

            elif category == 'date' and values:
                # Handle the possible values for the 'date' filter
                date_value = values[0] if isinstance(values, list) else values
                if date_value in date_mapping:
                    months = date_mapping[date_value]
                    now = datetime.now()
                    start_date = now - timedelta(days=months * 30)
                    filter_criteria &= Q(created_at__gte=start_date)  # Use 'created_at' column for filtering
                else:
                    return JsonResponse({'error': f'Invalid value for date filter: {date_value}'}, status=400)

        queryset = queryset.filter(filter_criteria)
        print(queryset)

        # Prepare unique results for the response
        unique_results = {}
        for entry in queryset:
            procrun_id = entry.get('id')
            tomogram_id = entry.get('run_pipe_run_id')
            if procrun_id not in unique_results and tomogram_id is not None:  # Ensure we only count entries with tomograms
                proc_run_created_at = datetime.fromisoformat(str(entry.get('created_at'))).strftime('%Y-%m-%d') if entry.get('created_at') else None
                cryogrid_created_at = datetime.fromisoformat(str(entry.get('cryogrid_created_at'))).strftime('%Y-%m-%d') if entry.get('cryogrid_created_at') else None
                response_model = ResponseModel(
                    tomograms=TomogramModel(id=tomogram_id, name="{} (id={})".format(entry.get('name'), tomogram_id), url=f"{base_url}/admin/processes/tomograms/{tomogram_id}"),
                    procPlan=ProcPlanModel(id=entry.get('proc_plan_plan_id'), name=entry.get('proc_plan_name'), url=f"{base_url}/admin/processes/procplan/{entry.get('proc_plan_plan_id')}"),
                    procRun=ProcRunModel(id=procrun_id, notes=entry.get('notes'), createdAt=str(proc_run_created_at)),
                    grid=GridModel(
                        id=entry.get('cryogrid_id'),
                        name="{} (id={})".format(entry.get('cryogrid_name'), entry.get('cryogrid_id')),
                        trashed=entry.get('cryogrid_trashed'),
                        url=f"{base_url}/admin/cryo_grids/cryogrid/{entry.get('cryogrid_id')}",
                        createdAt=str(cryogrid_created_at)
                    ),
                    project=ProjectModel(id=entry.get('project_id'), name=entry.get('project_name'), url=f"{base_url}/admin/projects/project/{entry.get('project_id')}"),
                    user=UserModel(id=entry.get('user_id'), name=entry.get('user_name').split('@')[0] if '@' in entry.get('user_name') else entry.get('user_name')),
                    msiSession=MSISessionModel(
                        id=entry.get('msi_session_id'),
                        name=entry.get('msi_session_name'),
                        url=f"{base_url}/admin/tem/msisession/{entry.get('msi_session_id')}"
                    )
                )
                unique_results[procrun_id] = response_model.dict()

        response_data = list(unique_results.values())

        # Paginate the formatted response data using Django's Paginator
        paginator = Paginator(response_data, page_size)
        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

        # Final response structure with pagination applied to formatted response data
        result = {
            'result': list(paginated_data),  # Contains only the paginated items for the current page
            'pagination': {
                'page': paginated_data.number,  # Current page number
                'pageSize': int(page_size),  # Items per page
                'totalPages': paginator.num_pages,  # Total number of pages
                'totalResults': paginator.count,  # Total number of items across all pages
            },
            'sortBy': {
                'sort': sort_field,
                'asc': asc
            }
        }

        return JsonResponse(result, safe=False)
    except UnprocessableEntity as e:
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
