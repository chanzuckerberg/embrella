from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProcRunForm, ReserveFrameProcRunForm, UpdateNotesForm
from django.contrib.auth.decorators import login_required
from . import models
from django.views.decorators.csrf import csrf_exempt
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
from cryo_grids.models import CryoGrid, PlungeFreezingSession, Specimen, Sample
from processes.models import *
from processes.utils import QueryParams, InputTomogramModel,AnnotationModel, AnnotationResponseModel, annotationQueryParams,SortMetadataModel, TomogramModel, tomoQueryParams, UnprocessableEntity, ResponseModel, ProcPlanModel, ProcRunModel,ProjectModel,JsonModel,GridModel,PaginationMetadataModel, UserModel,MSISessionModel
from tem.models import MsiSession
from processes.scripts.import_tomograms import get_available_sessions, main as import_tomograms_main
from django.db.models import F,Q
from django.http import JsonResponse
from pydantic import ValidationError
from typing import List
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import logging
import os
from django.forms.models import model_to_dict  # ensure this is imported
# from umbrella.settings import ENVIRONMENT
import asyncio
import glob
import requests
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup
from asgiref.sync import sync_to_async
import io
import sys
from contextlib import redirect_stdout
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
    
@csrf_exempt
# @login_required
def create_run(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))  # Parse JSON data
            plan_id = int(data.get('proc_plan'))  # Extract `proc_plan`
            session_id = int(data.get('msi_session'))  # Extract `msi_session`

            msi_session = MsiSession.objects.get(pk=session_id)
            proc_plan = ProcPlan.objects.get(pk=plan_id)
            name = suggest_name('run', msi_session, proc_plan)

            run_instance = ProcRun.objects.create(
                name=name,
                msi_session=msi_session,
                proc_plan=proc_plan,
            )
            run_instance.save()
            run_instance.save_pipe_run_data()
            run_instance.create_tomogram_collection()

            return HttpResponseRedirect(reverse('processes:detail', args=(run_instance.id,)))

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except KeyError as e:
            return JsonResponse({'error': f'Missing key: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

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
        filter_criteria = Q()
        queryset = ProcRun.objects.select_related(
            'proc_plan',
            'msi_session',
            'freezing_session',
            'msi_session__project',
            'msi_session__grid',
            'msi_session__user',
            'msi_session__atlas_session',
            'msi_session__atlas_session__group',
            'msi_session__grid__specimen'
        ).prefetch_related(
            'msi_session__grid__specimen__samples',  # Updated: prefetch the samples (many-to-many)
            'runpipedata_set__tomograms_set'
        ).filter(filter_criteria, proc_plan__name__in=['czii-live', 'czii-denoise'])

        # Add date ranges
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
                        item['selected'] = item_name.strip().lower() in {
                            val.lower() for val in selected_values if isinstance(val, str)
                        }
                    else:
                        item['selected'] = False

        # Aggregating counts for each filter
        filters = {
            'project': list(
                queryset.values(project_name=F('msi_session__project__name'))
                .annotate(count=Count('id'))
                .order_by('project_name')
                .values(name=F('project_name'), count=F('count'))
            ),
            'sample': [],
            'user': list(
                queryset.annotate(
                    user_temp_name=Trim(
                        Case(
                            When(
                                msi_session__user__username__contains='@',
                                then=Substr(
                                    F('msi_session__user__username'),
                                    1,
                                    StrIndex(F('msi_session__user__username'), Value('@')) - 1
                                )
                            ),
                            default=F('msi_session__user__username'),
                            output_field=CharField()
                        )
                    )
                )
                .values(user_temp_name=F('user_temp_name'))
                .annotate(count=Count('id'))
                .order_by('user_temp_name')
                .values(name=F('user_temp_name'), count=F('count'))
            ),
            'msiSession': list(
                queryset.exclude(msi_session__name__isnull=True)
                .values(session_name=F('msi_session__name'))
                .annotate(count=Count('id'))
                .order_by('session_name')
                .values(name=F('session_name'), count=F('count'))
            ),
            'screeningSession': list(
                queryset.exclude(msi_session__atlas_session__group__name__isnull=True)
                .values(screening_session_name=F('msi_session__atlas_session__group__name'))
                .annotate(count=Count('id'))
                .order_by('screening_session_name')
                .values(name=F('screening_session_name'), count=F('count'))
            ),
            'procPlan': list(
                queryset.filter(
                    proc_plan__name__in=['czii-denoise', 'czii-live']
                )
                .values(plan_name=F('proc_plan__name'))
                .annotate(count=Count('id'))
                .order_by('plan_name')
                .values(name=F('plan_name'), count=F('count'))
            ),
            'date': [
                {
                    "name": key,
                    "count": queryset.filter(updated_at__gte=value).count()
                }
                for key, value in date_ranges.items()
            ],
        }

        # Process samples from the many-to-many relationship (updated)
        sample_data = (
            queryset.values(
                sample_name=F('msi_session__grid__specimen__samples__name'),
            )
            .annotate(count=Count('id', distinct=True))
            .order_by('sample_name')
        )

        processed_samples = {}
        for item in sample_data:
            sample_name = item['sample_name']
            if sample_name is None:
                continue
            if sample_name in processed_samples:
                processed_samples[sample_name]['count'] += item['count']
            else:
                try:
                    sample_obj = Sample.objects.get(name=sample_name)
                    display_name = sample_obj.name
                    if sample_obj.ontology:
                        display_name += f" ({sample_obj.ontology})"
                except Sample.DoesNotExist:
                    display_name = sample_name
                processed_samples[sample_name] = {
                    'name': display_name,
                    'count': item['count'],
                    'selected': False
                }
        filters['sample'] = list(processed_samples.values())

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
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    
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

        query_data = request.GET.dict()
        query_data['q'] = q_param

        # Validate query parameters
        try:
            query_params = tomoQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        # Pagination and sorting defaults
        page = int(request.GET.get('page', 1))  # Default to first page
        page_size = int(request.GET.get('pageSize', 10))  # Default page size is 10
        sort_field = 'updated_at'
        asc = False

        # Helper function to extract values
        def extract_value(value):
            return value[0] if isinstance(value, list) and value else value

        # Override pagination and sorting if provided in q_param
        for item in q_param:
            if item['category'] == 'sort':
                sort_value = extract_value(item['value'])
                if sort_value == 'updatedAt':
                    sort_field = 'updated_at'
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
            'proc_plan',
            'msi_session',
            'freezing_session',
            'msi_session__project',
            'msi_session__grid',
            'msi_session__user',
            'msi_session__atlas_session',
            'msi_session__atlas_session__group',
            'msi_session__grid__specimen'
        ).prefetch_related(
            'msi_session__grid__specimen__samples',  # Updated prefetch: use many-to-many field "samples"
            'runpipedata_set'
        ).filter(
            proc_plan__name__in=['czii-live', 'czii-denoise']
        ).values(
            'id',
            'name',
            'notes',
            'created_at',
            'updated_at',
            'proc_plan_id',
            'msi_session_id',
            tomograms_id=F('runpipedata__tomograms__id'),
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
            specimen_id=F('msi_session__grid__specimen__id'),
            screening_session_name=F('msi_session__atlas_session__group__name'),
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
            elif category == 'user':
                user_filter = Q()
                for value in values:
                    user_filter |= Q(msi_session__user__username__startswith=value)
                filter_criteria &= user_filter
            elif category == 'screeningSession':
                session_filter = Q()
                for value in values:
                    if value is None:
                        session_filter |= Q(msi_session__atlas_session__group__name__isnull=True)
                    else:
                        session_filter |= Q(msi_session__atlas_session__group__name__icontains=value)
                filter_criteria &= session_filter
            elif category == 'grid':
                filter_criteria &= Q(msi_session__grid__name__in=values)
            elif category == 'project':
                filter_criteria &= Q(msi_session__project__name__in=values)
            elif category == 'msiSession':
                session_name_filter = Q()
                for value in values:
                    if value is None:
                        session_name_filter |= Q(msi_session__name__isnull=True)
                    else:
                        session_name_filter |= Q(msi_session__name__icontains=value)
                filter_criteria &= session_name_filter
            elif category == 'tomograms':
                filter_criteria &= Q(name__in=values)
            elif category == 'date' and values:
                date_value = values[0] if isinstance(values, list) else values
                if date_value in date_mapping:
                    months = date_mapping[date_value]
                    now_dt = datetime.now()
                    start_date = now_dt - timedelta(days=months * 30)
                    filter_criteria &= Q(updated_at__gte=start_date)
                else:
                    return JsonResponse({'error': f'Invalid value for date filter: {date_value}'}, status=400)
            elif category == 'sample':
                # Updated sample filtering using the many-to-many field "samples"
                sample_filter = Q()
                for value in values:
                    if value is None:
                        sample_filter |= Q(msi_session__grid__specimen__samples__isnull=True)
                    elif "with " in value:
                        parts = value.split(" with ")
                        sample_name = parts[0].strip()
                        ontology_value = parts[1].strip() if len(parts) > 1 else None
                        sample_filter |= Q(
                            msi_session__grid__specimen__samples__name=sample_name,
                            msi_session__grid__specimen__samples__ontology__icontains=ontology_value
                        )
                    elif "without tag" in value:
                        sample_name = value.replace(" without tag", "").strip()
                        sample_filter |= Q(
                            msi_session__grid__specimen__samples__name=sample_name
                        ) & (Q(msi_session__grid__specimen__samples__ontology='') | Q(msi_session__grid__specimen__samples__ontology__isnull=True))
                    else:
                        sample_filter |= Q(msi_session__grid__specimen__samples__name=value)
                filter_criteria &= sample_filter

        queryset = queryset.filter(filter_criteria)

        # Prepare unique results for the response
        unique_results = {}
        base_url = get_base_url()  # Assuming this function exists
        for entry in queryset:
            procrun_id = entry.get('id')
            tomogram_id = entry.get('tomograms_id')
            if procrun_id not in unique_results and tomogram_id is not None:
                proc_run_updated_at = datetime.fromisoformat(str(entry.get('updated_at'))).strftime('%Y-%m-%d') if entry.get('updated_at') else None
                cryogrid_created_at = datetime.fromisoformat(str(entry.get('cryogrid_created_at'))).strftime('%Y-%m-%d') if entry.get('cryogrid_created_at') else None
                response_model = ResponseModel(
                    tomograms=TomogramModel(
                        id=tomogram_id,
                        name="{} (id={})".format(entry.get('name'), tomogram_id),
                        url=f"{base_url}/admin/processes/tomograms/{tomogram_id}"
                    ),
                    procPlan=ProcPlanModel(
                        id=entry.get('proc_plan_plan_id'),
                        name=entry.get('proc_plan_name'),
                        url=f"{base_url}/admin/processes/procplan/{entry.get('proc_plan_plan_id')}"
                    ),
                    procRun=ProcRunModel(
                        id=procrun_id,
                        notes=entry.get('notes'),
                        updatedAt=str(proc_run_updated_at)
                    ),
                    grid=GridModel(
                        id=entry.get('cryogrid_id'),
                        name="{} (id={})".format(entry.get('cryogrid_name'), entry.get('cryogrid_id')),
                        trashed=entry.get('cryogrid_trashed'),
                        url=f"{base_url}/admin/cryo_grids/cryogrid/{entry.get('cryogrid_id')}",
                        createdAt=str(cryogrid_created_at)
                    ),
                    project=ProjectModel(
                        id=entry.get('project_id'),
                        name=entry.get('project_name'),
                        url=f"{base_url}/admin/projects/project/{entry.get('project_id')}"
                    ),
                    user=UserModel(
                        id=entry.get('user_id'),
                        name=entry.get('user_name').split('@')[0] if '@' in entry.get('user_name') else entry.get('user_name')
                    ),
                    msiSession=MSISessionModel(
                        id=entry.get('msi_session_id'),
                        name=entry.get('msi_session_name'),
                        url=f"{base_url}/admin/tem/msisession/{entry.get('msi_session_id')}"
                    )
                )
                unique_results[procrun_id] = response_model.dict()

        response_data = list(unique_results.values())

        # Add metadata_url to each result
        for item in response_data:
            session_name = item.get('msiSession', {}).get('name')
            run_number = item.get('tomograms', {}).get('name')
            print(run_number)
            if session_name and run_number:
                # Extract just the run number part before the ID
                if " (id=" in run_number:
                    run_number = run_number.split(" (id=")[0]
                item['metadata_url'] = f"{base_url}/metadata/view/{session_name}/{run_number}"
            else:
                item['metadata_url'] = None        

        # Paginate the formatted response data using Django's Paginator
        paginator = Paginator(response_data, page_size)
        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

        result = {
            'result': list(paginated_data),
            'pagination': {
                'page': paginated_data.number,
                'pageSize': int(page_size),
                'totalPages': paginator.num_pages,
                'totalResults': paginator.count,
            },
            'sortBy': SortMetadataModel(
                sort='updatedAt' if sort_field is not None else None,
                asc=asc
            ).model_dump()
        }

        return JsonResponse(result, safe=False)
    except UnprocessableEntity as e:
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    

@require_http_methods(["GET"])
def available_annotation_filter(request):
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

        # Build base filter criteria (if any additional criteria are needed)
        filter_criteria = Q()

        # Updated queryset: prefetch the many-to-many "samples" field from Specimen.
        queryset = Annotation.objects.select_related(
            'msi_session',
            'msi_session__project',
            'msi_session__user',
            'msi_session__grid',
            'msi_session__grid__specimen',
            'msi_session__grid__gridpreparationlog',
            'msi_session__atlas_session__group',
            'pipe_data__run__proc_plan'
        ).prefetch_related(
            'msi_session__grid__specimen__samples'
        ).exclude(
            pipe_data__run__proc_plan__name__in=['czii-live', 'czii-denoise']
        ).values(
            'id',
            'updated_at',
            annotation_name=F('name'),
            project_display_name=F('msi_session__project__name'),
            user_display_name=F('msi_session__user__username'),
            grid_display_name=F('msi_session__grid__name'),
            specimen_protocol=F('msi_session__grid__specimen__notes'),
            grid_preparation_log_blot_time=F('msi_session__grid__blot_time'),
            # Updated: use the many-to-many "samples" field for specimen sample name and ontology
            specimen_sample=F('msi_session__grid__specimen__samples__name'),
            specimen_tags=F('msi_session__grid__specimen__samples__ontology'),
            screen_session_display_name=F('msi_session__atlas_session__group__name'),
            proc_plan_display_name=F('pipe_data__run__proc_plan__name')
        ).filter(filter_criteria)

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
                        item['selected'] = item_name.strip().lower() in {
                            val.lower() for val in selected_values if isinstance(val, str)
                        }
                    else:
                        item['selected'] = False

        # Aggregating counts for each filter
        filters = {
            'project': list(
                queryset.values(project_name=F('project_display_name'))
                .annotate(count=Count('id'))
                .order_by('project_name')
                .values(name=F('project_name'), count=F('count'))
            ),
            'user': list(
                queryset.annotate(
                    user_temp_name=Trim(
                        Case(
                            When(
                                user_display_name__contains='@',
                                then=Substr(
                                    F('user_display_name'),
                                    1,
                                    StrIndex(F('user_display_name'), Value('@')) - 1
                                )
                            ),
                            default=F('user_display_name'),
                            output_field=CharField()
                        )
                    )
                )
                .values(user_temp_name=F('user_temp_name'))
                .annotate(count=Count('id'))
                .order_by('user_temp_name')
                .values(name=F('user_temp_name'), count=F('count'))
            ),
            'msiSession': list(
                queryset.exclude(msi_session__name__isnull=True)
                .values(msi_session_name=F('msi_session__name'))
                .annotate(count=Count('id'))
                .order_by('msi_session_name')
                .values(name=F('msi_session_name'), count=F('count'))
            ),
            'screeningSession': list(
                queryset.exclude(screen_session_display_name__isnull=True)
                .values(screen_session_name=F('screen_session_display_name'))
                .annotate(count=Count('id'))
                .order_by('screen_session_name')
                .values(name=F('screen_session_name'), count=F('count'))
            ),
            'sample': list(
                queryset.values(sample_name=F('specimen_sample'))
                .annotate(count=Count('id', distinct=True))
                .order_by('sample_name')
                .values(name=F('sample_name'), count=F('count'))
            ),
            'grid': list(
                queryset.values(grid_name=F('grid_display_name'))
                .annotate(count=Count('id'))
                .order_by('grid_name')
                .values(name=F('grid_name'), count=F('count'))
            ),
            'procPlan': list(
                queryset.values(proc_plan_name=F('proc_plan_display_name'))
                .annotate(count=Count('id'))
                .order_by('proc_plan_name')
                .values(name=F('proc_plan_name'), count=F('count'))
            ),
            'date': [
                {
                    "name": key,
                    "count": queryset.filter(updated_at__gte=value).count()
                }
                for key, value in date_ranges.items()
            ],
        }

        # Process samples to ensure exclusive categorization as "with ontology" or "without ontology"
        sample_data = (
            queryset.values(
                sample_name=F('msi_session__grid__specimen__samples__name'),
                ontology=F('msi_session__grid__specimen__samples__ontology')
            )
            .annotate(count=Count('id'))
            .order_by('sample_name', 'ontology')
        )

        processed_samples = {}
        for item in sample_data:
            sample_name = item['sample_name']
            ontology = item.get('ontology')
            if not sample_name:
                continue
            if sample_name not in processed_samples:
                # Use ontology information if available
                display_name = f"{sample_name}"
                processed_samples[sample_name] = {
                    'name': display_name,
                    'count': item['count'],
                    'selected': False
                }
            else:
                processed_samples[sample_name]['count'] += item['count']

        filters['sample'] = list(processed_samples.values())

        # Apply 'selected' status to all filters
        for key, filter_list in filters.items():
            add_selected_status(filter_list, key)

        response_data = {
            "filters": filters
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@require_http_methods(["GET"])
def get_annotation_details(request):
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

        query_data = request.GET.dict()
        query_data['q'] = q_param

        # Validate query parameters
        try:
            query_params = annotationQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        # Pagination and sorting defaults
        page = int(request.GET.get('page', 1))  # Default to first page
        page_size = int(request.GET.get('pageSize', 10))  # Default page size is 10
        sort_field = 'updated_at'
        asc = True

        # Override pagination and sorting if provided in q_param
        def extract_value(value):
            return value[0] if isinstance(value, list) and value else value

        for item in q_param:
            if item['category'] == 'sort':
                sort_value = extract_value(item['value'])
                if sort_value == 'updatedAt':
                    sort_field = 'updated_at'
                else:
                    sort_field = sort_value
            elif item['category'] == 'asc':
                asc_value = extract_value(item['value'])
                asc = bool(asc_value) if isinstance(asc_value, bool) else asc_value.lower() == 'true'
            elif item['category'] == 'page':
                page = int(extract_value(item['value']))
            elif item['category'] == 'pageSize':
                page_size = int(extract_value(item['value']))

        date_mapping = {
            'last_1_month': 1,
            'last_3_months': 3,
            'last_6_months': 6
        }

        # Determine sort order
        sort_order = sort_field if asc else f'-{sort_field}'

        # Base queryset
        queryset = Annotation.objects.select_related(
            'pipe_data__run__proc_plan',
            'pipe_data__run__msi_session',
            'pipe_data__run__msi_session__project',
            'pipe_data__run__msi_session__grid',
            'pipe_data__run__msi_session__user',
            'pipe_data__run__msi_session__atlas_session__group',
            'tomograms',
            'tomograms__pipe_data',  # Join on processes_runpipedata
            'tomograms__pipe_data__run'
        ).exclude(
            pipe_data__run__proc_plan__name__in=['czii-live', 'czii-denoise']
        ).values(
            'id',
            'updated_at',
            'notes',
            annotation_name=F('name'),
            annotation_id=F('id'),
            annotation_updated_at=F('updated_at'),
            proc_plan_id=F('pipe_data__run__proc_plan__id'),
            proc_plan_name=F('pipe_data__run__proc_plan__name'),
            proc_run_id=F('pipe_data__run__id'),
            proc_run_display_name=F('pipe_data__run__name'),
            proc_run_note=F('pipe_data__run__notes'),
            proc_run_updated_at=F('pipe_data__run__updated_at'),
            json_id=F('pipe_data__run__json_path_id'),
            cryogrid_id=F('pipe_data__run__msi_session__grid__id'),
            cryogrid_name=F('pipe_data__run__msi_session__grid__name'),
            cryogrid_trashed=F('pipe_data__run__msi_session__grid__trashed'),
            cryogrid_created_at=F('pipe_data__run__msi_session__grid__updated_on'),
            project_id=F('pipe_data__run__msi_session__project__id'),
            project_name=F('pipe_data__run__msi_session__project__name'),
            user_id=F('pipe_data__run__msi_session__user__id'),
            user_name=F('pipe_data__run__msi_session__user__username'),
            msi_session_identifier=F('pipe_data__run__msi_session__id'),
            msi_session_name=F('pipe_data__run__msi_session__name'),
            tomogram_id=F('tomograms__id'),
            tomogram_name=F('tomograms__pipe_data__run__name')
        ).order_by(sort_order)
        # print(queryset)
        # Apply filters from q_param
        filter_criteria = Q()
        for item in q_param:
            category = item['category']
            values = item['value']

            if category == 'procPlan':
                filter_criteria &= Q(pipe_data__run__proc_plan__name__in=values)
            elif category == 'user':
                user_filter = Q()
                for value in values:
                    user_filter |= Q(pipe_data__run__msi_session__user__username__icontains=value)
                filter_criteria &= user_filter
            elif category == 'grid':
                filter_criteria &= Q(pipe_data__run__msi_session__grid__name__in=values)
            elif category == 'project':
                filter_criteria &= Q(pipe_data__run__msi_session__project__name__in=values)
            elif category == 'date' and values:
                # Handle the possible values for the 'date' filter
                date_value = values[0] if isinstance(values, list) else values
                if date_value in date_mapping:
                    months = date_mapping[date_value]
                    now_dt = datetime.now()
                    start_date = now_dt - timedelta(days=months * 30)
                    filter_criteria &= Q(updated_at__gte=start_date)
                else:
                    return JsonResponse({'error': f'Invalid value for date filter: {date_value}'}, status=400)
            elif category == 'msiSession':
                session_name_filter = Q()
                for value in values:
                    if value is None:
                        session_name_filter |= Q(msi_session__name__isnull=True)
                    else:
                        session_name_filter |= Q(msi_session__name__icontains=value)
                filter_criteria &= session_name_filter
            elif category == 'screeningSession':
                session_filter = Q()
                for value in values:
                    if value is None:
                        session_filter |= Q(msi_session__atlas_session__group__name__isnull=True)
                    else:
                        session_filter |= Q(msi_session__atlas_session__group__name__icontains=value)
                filter_criteria &= session_filter
            elif category == 'sample':
                sample_filter = Q()
                for value in values:
                    # Updated sample filter using the many-to-many relationship on specimens
                    if "with " in value:
                        parts = value.split(" with ")
                        sample_name = parts[0].strip()
                        ontology_value = parts[1].strip() if len(parts) > 1 else None
                        sample_filter |= Q(
                            pipe_data__run__msi_session__grid__specimen__samples__name=sample_name,
                            pipe_data__run__msi_session__grid__specimen__samples__ontology__icontains=ontology_value
                        )
                    elif "without tag" in value:
                        sample_name = value.replace(" without tag", "").strip()
                        sample_filter |= Q(
                            pipe_data__run__msi_session__grid__specimen__samples__name=sample_name
                        ) & (Q(pipe_data__run__msi_session__grid__specimen__samples__ontology='') | Q(pipe_data__run__msi_session__grid__specimen__samples__ontology__isnull=True))
                    else:
                        sample_filter |= Q(pipe_data__run__msi_session__grid__specimen__samples__name=value)
                filter_criteria &= sample_filter

        queryset = queryset.filter(filter_criteria)

        # Prepare unique results for the response
        response_data = [] 
        for entry in queryset:
            procrun_id = entry.get('proc_run_id')  # Using `proc_run_id` from the query
            # print(procrun_id)
            json_id = entry.get('json_id')  # Using `json_id` if available
            cryogrid_created_at = (
                datetime.fromisoformat(str(entry.get('cryogrid_created_at'))).strftime('%Y-%m-%d')
                if entry.get('cryogrid_created_at') else None
            )
            proc_run_updated_at = (
                datetime.fromisoformat(str(entry.get('proc_run_updated_at'))).strftime('%Y-%m-%d')
                if entry.get('proc_run_updated_at') else None
            )

            response_model = AnnotationResponseModel(
                annotations=AnnotationModel(
                    id=entry.get('annotation_id'),
                    name=f"{entry.get('proc_run_display_name')} (id={entry.get('annotation_id')})",
                    url=f"{base_url}/admin/processes/annotation/{entry.get('annotation_id')}/",
                    updatedAt=datetime.fromisoformat(str(entry.get('annotation_updated_at'))).strftime('%Y-%m-%d'),
                    notes=f"{entry.get('notes')}"
                ),
                procPlan=ProcPlanModel(
                    id=entry.get('proc_plan_id'),
                    name=entry.get('proc_plan_name'),
                    url=f"{base_url}/admin/processes/procplan/{entry.get('proc_plan_id')}"
                ),
                inputTomogram=InputTomogramModel(
                    id=entry.get('tomogram_id'),
                    name="{} (id={})".format(entry.get('tomogram_name'), entry.get('tomogram_id')),
                    url=f"{base_url}/admin/processes/tomograms/{entry.get('tomogram_id')}"
                ),
                json=JsonModel(
                    id=1,
                    name="/24sep11c/{run}/deno/denoiset/run001/den001/"
                ),
                grid=GridModel(
                    id=entry.get('cryogrid_id'),
                    name=f"{entry.get('cryogrid_name')} (id={entry.get('cryogrid_id')})",
                    trashed=entry.get('cryogrid_trashed'),
                    url=f"{base_url}/admin/cryo_grids/cryogrid/{entry.get('cryogrid_id')}",
                    createdAt=cryogrid_created_at
                ),
                project=ProjectModel(
                    id=entry.get('project_id'),
                    name=entry.get('project_name'),
                    url=f"{base_url}/admin/projects/project/{entry.get('project_id')}"
                ),
                user=UserModel(
                    id=entry.get('user_id'),
                    name=entry.get('user_name').split('@')[0] if '@' in entry.get('user_name') else entry.get('user_name')
                ),
                msiSession=MSISessionModel(
                    id=entry.get('msi_session_identifier'),
                    name=entry.get('msi_session_name'),
                    url=f"{base_url}/admin/tem/msisession/{entry.get('msi_session_identifier')}"
                )
            )
            response_data.append(response_model.dict())

        # Paginate the formatted response data using Django's Paginator
        paginator = Paginator(response_data, page_size)
        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

        result = {
            'result': list(paginated_data),  # Contains only the paginated items for the current page
            'pagination': {
                'page': paginated_data.number,  # Current page number
                'pageSize': int(page_size),       # Items per page
                'totalPages': paginator.num_pages,  # Total number of pages
                'totalResults': paginator.count,    # Total number of items across all pages
            },
            'sortBy': SortMetadataModel(
                sort='updatedAt' if sort_field is not None else None,
                asc=asc
            ).model_dump()
        }

        return JsonResponse(result, safe=False)

    except UnprocessableEntity as e:
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)

@require_http_methods(["GET"])
def get_session_id(request):
    """
    API endpoint to get MSI session ID by session name.
    URL: /processes/api/get-session-id?name=SESSION_NAME
    """
    try:
        session_name = request.GET.get('name')
        if not session_name:
            return JsonResponse({'error': 'Session name parameter is required'}, status=400)
        
        # Query the MsiSession model to find a session with the provided name
        session = MsiSession.objects.filter(name=session_name).first()
        
        if not session:
            return JsonResponse({'error': f'No session found with name: {session_name}'}, status=404)
        
        # Return the session ID
        return JsonResponse({'id': session.id, 'name': session.name})
    
    except Exception as e:
        logger.error(f'Error getting session ID: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    

@require_http_methods(["GET"])
def sync_tomograms_view(request):
    """View for the tomogram sync page"""
    # Run the async function in an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sessions = loop.run_until_complete(get_available_sessions())
    loop.close()
    
    return render(request, 'customs/sync_tomograms.html', {'sessions': sessions})

@require_http_methods(["GET"])
def get_runs(request):
    """API endpoint to get runs for a session"""
    session_id = request.GET.get('session')
    try:
        session = MsiSession.objects.get(id=session_id)
        # Get unique run IDs from Review table for this session
        runs = Review.objects.filter(session=session).values('run_id').distinct()
        runs_data = [{'runId': run['run_id']} for run in runs]
        return JsonResponse({'runs': runs_data})
    except MsiSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

def get_zarr_files(session_name, run_id, recon_type):
    """Get zarr files from the specified path"""
    if recon_type.lower() == 'sart':
        vol_dir = 'vol003'
        job_name = 'aretomo3'
    elif recon_type.lower() == 'dctf':
        vol_dir = 'vol001'
        job_name = 'aretomo3'
    else:  # denoised
        vol_dir = ''
        job_name = 'denoise'
    base_path = f"https://czii-onsite.czbiohub.org/krios1.processing/{job_name}/{session_name}/{run_id}"
    
    # Construct the full path
    if vol_dir:
        full_path = f"{base_path}/{vol_dir}"
    else:
        full_path = base_path
    
    # Get all zarr files
    try:
        # Make a request to list the directory contents
        response = requests.get(full_path)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        file_rows = soup.find_all('tr', class_='file')
        valid_zarr_files = []

        for row in file_rows:
            name_tag = row.find('span', class_='name')
            if name_tag:
                filename = name_tag.text.strip()
                print(filename)
                # Check if it's a zarr directory (ends with .zarr/)
                if filename.endswith('.zarr/'):
                    # Remove the trailing slash to get the actual filename
                    filename = filename[:-1]
                    valid_zarr_files.append(filename)
        return valid_zarr_files

    except requests.RequestException as e:
        print(f"❌ Failed to fetch ZARR files from web: {e}")
        return []

@require_http_methods(["GET"])
def get_tomogram_stats(request):
    """API endpoint to get tomogram statistics"""
    session_id = request.GET.get('session')
    run_id = request.GET.get('run')
    recon_type = request.GET.get('type', '').lower()

    try:
        session = MsiSession.objects.get(id=session_id)
        # Get zarr files for the selected configuration
        zarr_files = get_zarr_files(session.name, run_id, recon_type)
        
        # Try to get the review, but don't fail if it doesn't exist
        try:
            review = Review.objects.get(
                session=session,
                run_id=run_id,
                reconstruction_type=recon_type
            )
            total = ReviewTomogram.objects.filter(review=review).count()
        except Review.DoesNotExist:
            total = 0
        
        # Count of generated tomograms (those that have corresponding zarr files)
        generated = len(zarr_files)
        return JsonResponse({
            'total': total,
            'generated': generated,
            'zarr_files': zarr_files  # Include the list of zarr files in the response
        })
    except MsiSession.DoesNotExist:
        return JsonResponse({
            'error': 'Session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
    
@require_http_methods(["POST"])
async def start_sync(request):
    """API endpoint to start tomogram sync process"""
    session_id = request.POST.get('session')
    run_id = request.POST.get('run')
    recon_type = request.POST.get('reconType')

    print(f"Received parameters - session_id: {session_id}, run_id: {run_id}, recon_type: {recon_type}")

    if not all([session_id, run_id, recon_type]):
        return JsonResponse({
            'success': False,
            'message': 'Missing required parameters'
        }, status=400)

    try:
        # First check if session exists - using sync_to_async
        session = await sync_to_async(MsiSession.objects.get)(id=session_id)
        print(f"Found session: {session.name}")

        # Check all reviews for this session to see what's available
        all_reviews = await sync_to_async(list)(Review.objects.filter(session=session))
        print(f"All reviews for this session: {[{'run_id': r.run_id, 'reconstruction_type': r.reconstruction_type} for r in all_reviews]}")

        # Get review with joined session data in a single query - using case-insensitive comparison
        review = await sync_to_async(Review.objects.select_related('session').get)(
            session_id=session_id,
            run_id=run_id,
            reconstruction_type__iexact=recon_type  # Case-insensitive comparison
        )
        print(f"Found review: {review}")
        print(f"Associated session: {review.session}")
        
        # Capture stdout to get progress information
        output = io.StringIO()
        with redirect_stdout(output):
            # Start sync process using import_tomograms.py script - run in a thread pool
            await sync_to_async(import_tomograms_main)(review.review_id)
        
        # Get the captured output
        progress_output = output.getvalue()
        print("Sync process completed with output:", progress_output)
        
        return JsonResponse({
            'success': True,
            'message': 'Sync process completed successfully',
            'progress': progress_output
        })
    except MsiSession.DoesNotExist:
        print(f"Session {session_id} not found in database")
        return JsonResponse({
            'success': False,
            'message': f'Session with ID {session_id} not found'
        }, status=404)
    except Review.DoesNotExist:
        print(f"Review not found with parameters - session_id: {session_id}, run_id: {run_id}, recon_type: {recon_type}")
        return JsonResponse({
            'success': False,
            'message': f'Review not found for session {session_id}, run {run_id}, and type {recon_type}'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in start_sync: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
