"""
Filter-related view functions for processing data.

This module contains views for fetching available filter options based on user selections.
"""
import json
import logging
from datetime import timedelta

from cryo_grids.models import Sample
from django.db.models import Case, CharField, Count, F, Q, Value, When
from django.db.models.functions import StrIndex, Substr, Trim
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from pydantic import ValidationError
from rest_framework.decorators import api_view

from processes.models import Annotation, ProcRun
from processes.validation import QueryParams

from .utils import msi_session_sort_key

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns available filters for ProcRuns based on selected criteria passed via 'q' query param.",
    parameters=[
        OpenApiParameter(name='q', required=True, type=OpenApiTypes.STR, description='JSON-encoded filter list'),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 422: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
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
            'msi_session__grid__specimen',
        ).prefetch_related(
            'msi_session__grid__specimen__samples',  # Updated: prefetch the samples (many-to-many)
            'runpipedata_set__tomograms_set',
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
                .values(name=F('project_name'), count=F('count')),
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
                                    StrIndex(F('msi_session__user__username'), Value('@')) - 1,
                                ),
                            ),
                            default=F('msi_session__user__username'),
                            output_field=CharField(),
                        ),
                    ),
                )
                .values(user_temp_name=F('user_temp_name'))
                .annotate(count=Count('id'))
                .order_by('user_temp_name')
                .values(name=F('user_temp_name'), count=F('count')),
            ),
            'msiSession': sorted(
                list(
                    queryset.exclude(msi_session__name__isnull=True)
                    .values(session_name=F('msi_session__name'))
                    .annotate(count=Count('id'))
                    .values(name=F('session_name'), count=F('count')),
                ),
                key=lambda x: msi_session_sort_key(x['name']),
            ),
            'screeningSession': list(
                queryset.exclude(msi_session__atlas_session__group__name__isnull=True)
                .values(screening_session_name=F('msi_session__atlas_session__group__name'))
                .annotate(count=Count('id'))
                .order_by('screening_session_name')
                .values(name=F('screening_session_name'), count=F('count')),
            ),
            'procPlan': list(
                queryset.filter(
                    proc_plan__name__in=['czii-denoise', 'czii-live'],
                )
                .values(plan_name=F('proc_plan__name'))
                .annotate(count=Count('id'))
                .order_by('plan_name')
                .values(name=F('plan_name'), count=F('count')),
            ),
            'date': [
                {
                    "name": key,
                    "count": queryset.filter(updated_at__gte=value).count(),
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
                    'selected': False,
                }
        filters['sample'] = list(processed_samples.values())

        # Apply 'selected' status to filters
        for key, filter_list in filters.items():
            add_selected_status(filter_list, key)

        # Convert to the expected output format
        response_data = {
            "filters": filters,
        }

        return JsonResponse(response_data)
    except ValidationError as e:
        # Handle Pydantic validation errors
        return JsonResponse({'error': f'Invalid input: {e.errors()}'}, status=400)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns annotation filter options for filtering annotations in UI.",
    parameters=[
        OpenApiParameter(name='q', required=True, type=OpenApiTypes.STR),
    ],
    responses={200: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
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
            'pipe_data__run__proc_plan',
        ).prefetch_related(
            'msi_session__grid__specimen__samples',
        ).exclude(
            pipe_data__run__proc_plan__name__in=['czii-live', 'czii-denoise'],
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
            proc_plan_display_name=F('pipe_data__run__proc_plan__name'),
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
                .values(name=F('project_name'), count=F('count')),
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
                                    StrIndex(F('user_display_name'), Value('@')) - 1,
                                ),
                            ),
                            default=F('user_display_name'),
                            output_field=CharField(),
                        ),
                    ),
                )
                .values(user_temp_name=F('user_temp_name'))
                .annotate(count=Count('id'))
                .order_by('user_temp_name')
                .values(name=F('user_temp_name'), count=F('count')),
            ),
            'msiSession': sorted(
                list(
                    queryset.exclude(msi_session__name__isnull=True)
                    .values(msi_session_name=F('msi_session__name'))
                    .annotate(count=Count('id'))
                    .values(name=F('msi_session_name'), count=F('count')),
                ),
                key=lambda x: msi_session_sort_key(x['name']),
            ),
            'screeningSession': list(
                queryset.exclude(screen_session_display_name__isnull=True)
                .values(screen_session_name=F('screen_session_display_name'))
                .annotate(count=Count('id'))
                .order_by('screen_session_name')
                .values(name=F('screen_session_name'), count=F('count')),
            ),
            'sample': list(
                queryset.values(sample_name=F('specimen_sample'))
                .annotate(count=Count('id', distinct=True))
                .order_by('sample_name')
                .values(name=F('sample_name'), count=F('count')),
            ),
            'grid': list(
                queryset.values(grid_name=F('grid_display_name'))
                .annotate(count=Count('id'))
                .order_by('grid_name')
                .values(name=F('grid_name'), count=F('count')),
            ),
            'procPlan': list(
                queryset.values(proc_plan_name=F('proc_plan_display_name'))
                .annotate(count=Count('id'))
                .order_by('proc_plan_name')
                .values(name=F('proc_plan_name'), count=F('count')),
            ),
            'date': [
                {
                    "name": key,
                    "count": queryset.filter(updated_at__gte=value).count(),
                }
                for key, value in date_ranges.items()
            ],
        }

        # Process samples to ensure exclusive categorization as "with ontology" or "without ontology"
        sample_data = (
            queryset.values(
                sample_name=F('msi_session__grid__specimen__samples__name'),
                ontology=F('msi_session__grid__specimen__samples__ontology'),
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
                    'selected': False,
                }
            else:
                processed_samples[sample_name]['count'] += item['count']

        filters['sample'] = list(processed_samples.values())

        # Apply 'selected' status to all filters
        for key, filter_list in filters.items():
            add_selected_status(filter_list, key)

        response_data = {
            "filters": filters,
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
