"""
Annotation-related view functions for processing workflows.

This module contains views for listing and managing annotation data.
"""
import json
import logging
from datetime import datetime, timedelta

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from pydantic import ValidationError
from rest_framework.decorators import api_view

from processes.models import Annotation
from processes.validation import (
    AnnotationModel,
    AnnotationResponseModel,
    GridModel,
    InputTomogramModel,
    JsonModel,
    MSISessionModel,
    ProcPlanModel,
    SortMetadataModel,
    UnprocessableEntity,
    UserModel,
    annotationQueryParams,
    ProjectModel,
)

from .constants import get_base_url

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns detailed annotation data with filters, pagination, and sorting using 'q' param.",
    parameters=[
        OpenApiParameter(name='q', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='page', required=False, type=int),
        OpenApiParameter(name='pageSize', required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
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
            'last_6_months': 6,
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
            'tomograms__pipe_data__run',
        ).exclude(
            pipe_data__run__proc_plan__name__in=['czii-live', 'czii-denoise'],
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
            tomogram_name=F('tomograms__pipe_data__run__name'),
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
                            pipe_data__run__msi_session__grid__specimen__samples__ontology__icontains=ontology_value,
                        )
                    elif "without tag" in value:
                        sample_name = value.replace(" without tag", "").strip()
                        sample_filter |= Q(
                            pipe_data__run__msi_session__grid__specimen__samples__name=sample_name,
                        ) & (Q(pipe_data__run__msi_session__grid__specimen__samples__ontology='') | Q(pipe_data__run__msi_session__grid__specimen__samples__ontology__isnull=True))
                    else:
                        sample_filter |= Q(pipe_data__run__msi_session__grid__specimen__samples__name=value)
                filter_criteria &= sample_filter

        queryset = queryset.filter(filter_criteria)

        # Prepare unique results for the response
        base_url = get_base_url()
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
                    notes=f"{entry.get('notes')}",
                ),
                procPlan=ProcPlanModel(
                    id=entry.get('proc_plan_id'),
                    name=entry.get('proc_plan_name'),
                    url=f"{base_url}/admin/processes/procplan/{entry.get('proc_plan_id')}",
                ),
                inputTomogram=InputTomogramModel(
                    id=entry.get('tomogram_id'),
                    name="{} (id={})".format(entry.get('tomogram_name'), entry.get('tomogram_id')),
                    url=f"{base_url}/admin/processes/tomograms/{entry.get('tomogram_id')}",
                ),
                json=JsonModel(
                    id=1,
                    name="/24sep11c/{run}/deno/denoiset/run001/den001/",
                ),
                grid=GridModel(
                    id=entry.get('cryogrid_id'),
                    name=f"{entry.get('cryogrid_name')} (id={entry.get('cryogrid_id')})",
                    trashed=entry.get('cryogrid_trashed'),
                    url=f"{base_url}/admin/cryo_grids/cryogrid/{entry.get('cryogrid_id')}",
                    createdAt=cryogrid_created_at,
                ),
                project=ProjectModel(
                    id=entry.get('project_id'),
                    name=entry.get('project_name'),
                    url=f"{base_url}/admin/projects/project/{entry.get('project_id')}",
                ),
                user=UserModel(
                    id=entry.get('user_id'),
                    name=entry.get('user_name').split('@')[0] if '@' in entry.get('user_name') else entry.get('user_name'),
                ),
                msiSession=MSISessionModel(
                    id=entry.get('msi_session_identifier'),
                    name=entry.get('msi_session_name'),
                    url=f"{base_url}/admin/tem/msisession/{entry.get('msi_session_identifier')}",
                ),
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
                asc=asc,
            ).model_dump(),
        }

        return JsonResponse(result, safe=False)

    except UnprocessableEntity as e:
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)
