from django.shortcuts import render
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, Puck, CryoGridCassette, \
    PlungeFreezingSession, PlungeFreezingPlan
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from pydantic import ValidationError
from .utils import CryoGridsQueryParams, QueryParams, CryoGridResponseModel, PaginationMetadataModel, SortMetadataModel
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, F, Value, CharField, Count
from django.db.models.functions import Substr, StrIndex, Trim
from django.utils.timezone import now
from datetime import timedelta
from django.http import JsonResponse
from .models import CryoGrid, CryoGridBox
from datetime import datetime
from umbrella import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import os
import logging

logger = logging.getLogger(__name__)


def get_base_url():
       if settings.ENVIRONMENT == 'staging':
           return 'http://umbrella-dev.czbiohub.org'
       elif settings.ENVIRONMENT == 'production':
           return 'http://umbrella.czbiohub.org'
       else:  # development
           return 'http://localhost:8000' 
       


@require_http_methods(["GET"])
def get_all_grid_boxes(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    try:
        # Get all unique names of grid boxes
        unique_grid_boxes = CryoGridBox.objects.order_by('name').values('name').distinct()
        # Extract names into a list
        unique_names = [box['name'] for box in unique_grid_boxes]

        return JsonResponse({"unique_names": unique_names}, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def grid_boxes_view(request):
    # Assuming you have a way to get `data.id`, perhaps from a query parameter or some logic.
    data_id = request.GET.get('id')  # Example way to get data.id, adjust as needed.

    context = {
        'title': 'Gridboxes',
        'data': {
            'id': data_id
        }
    }
    return render(request, 'cryo_grids/detail.html', context)




def get_specific_grids(request):
    grid_box_name = request.GET.get('grid_box_name')
    username = request.GET.get('username')

    try:
        # Initialize the query set
        specific_grids = CryoGrid.objects.all()

        # Filter by grid box name if provided
        if grid_box_name:
            try:
                grid_box = CryoGridBox.objects.get(name=grid_box_name)
                specific_grids = specific_grids.filter(grid_box=grid_box)
            except CryoGridBox.DoesNotExist:
                return JsonResponse({"error": "Grid box not found."}, status=404)

        # Filter by username if provided
        if username:
            specific_grids = specific_grids.filter(user__username=username)

        # Join with the User and CryoGridCassette tables and select relevant fields
        specific_grids = specific_grids.select_related('grid_box', 'user', 'grid_cassette').values(
            'id', 'create_on', 'name', 'notes', 'position_in_box', 'grid_box_id',
            'clipped', 'trashed', 'slot_number_in_cassette', 'grid_cassette_id',
            'user__username', 'grid_cassette__name'
        )

        # Format the data
        grids_data = list(specific_grids)

        return JsonResponse(grids_data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

from django.views.decorators.csrf import csrf_exempt



@require_http_methods(["GET"])
def available_filters(request):
    try:
        # request.META['HTTP_ORIGIN'] = '*' # this is only for * 
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

        # Base queryset and your existing logic for processing the filters...
        # Base queryset with annotations for counting occurrences
        queryset = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user',
            'grid_cassette', 'freezing_plan'
        ).prefetch_related(
            'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        )

        current_time = now()
        date_ranges = {
            'last_1_month': current_time - timedelta(days=30),
            'last_3_months': current_time - timedelta(days=90),
            'last_6_months': current_time - timedelta(days=180),
        }

        # Function to add 'selected' key based on user selection
        def add_selected_status(filter_list, category):
            for item in filter_list:
                item_name = item['name']
                if isinstance(item_name, str):
                    item['selected'] = item_name in selected_filters.get(category, set())
                else:
                    item['selected'] = False

        # Aggregating counts for each filter (this part remains the same as your original logic)
        filters = {
            'project': list(queryset.annotate(project_temp_name=F('intended_project__name'))
                        .values(project_temp_name=F('project_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('project_temp_name')
                        .values(name=F('project_temp_name'), count=F('count'))),
            'puck': list(queryset.annotate(puck_temp_name=F('grid_box__puck__name'))
                        .values(puck_temp_name=F('puck_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('puck_temp_name')
                        .values(name=F('puck_temp_name'), count=F('count'))),
            'sample': list(queryset.annotate(sample_temp_name=F('freezing_plan__sample__name'))
                        .values(sample_temp_name=F('sample_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('sample_temp_name')
                        .values(name=F('sample_temp_name'), count=F('count'))),
            'user': list(queryset.annotate(
                            user_temp_name=Trim(
                                Case(
                                    When(user__username__contains='@',
                                         then=Substr(F('user__username'), 1, StrIndex(F('user__username'), Value('@')) - 1)),
                                    default=F('user__username'),
                                    output_field=CharField()
                                )
                            )
                        ).values(user_temp_name=F('user_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('user_temp_name')
                        .values(name=Trim(F('user_temp_name')), count=F('count'))),
            'cassette': list(queryset.annotate(cassette_temp_name=F('grid_cassette__name'))
                        .values(cassette_temp_name=F('cassette_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('cassette_temp_name')
                        .values(name=F('cassette_temp_name'), count=F('count'))),
            'screeningsession': list(queryset.filter(freezing_session__isnull=False)
                        .annotate(screen_session_temp_name=F('atlassession__group__name'))
                        .values(screen_session_temp_name=F('screen_session_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('screen_session_temp_name')
                        .values(name=F('screen_session_temp_name'), count=F('count'))),
            'msisession': list(queryset.filter(msisession__isnull=False)  # Exclude null msisession relations
                        .annotate(msi_session_temp_name=F('msisession__name'))
                        .values(msi_session_temp_name=F('msi_session_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('msi_session_temp_name')
                        .values(name=F('msi_session_temp_name'), count=F('count'))),
            'status': list(queryset.annotate(status_name=F('trashed'))
                       .values('status_name')
                       .annotate(count=Count('id'))
                       .order_by('trashed')
                       .values(name=F('status_name'), count=F('count'))),
            'date': [
                {"name": "last_1_month", "count": queryset.filter(create_on__gte=date_ranges['last_1_month']).count()},
                {"name": "last_3_months", "count": queryset.filter(create_on__gte=date_ranges['last_3_months']).count()},
                {"name": "last_6_months", "count": queryset.filter(create_on__gte=date_ranges['last_6_months']).count()}
            ]
        }

        # Process the 'sample' filter and replace sample_name with the detailed information
        processed_samples = []
        for item in filters['sample']:
            if 'name' in item:
                # Get the associated freezing plans based on the sample name
                freezing_plans = PlungeFreezingPlan.objects.filter(sample__name=item['name'])

                # Create a string that summarizes the freezing plan details
                freezing_plan_details = []
                for freezing_plan in freezing_plans:
                    tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
                    plan_str = f"{item['name']} with {tag_names}" if tag_names else f"{item['name']} without tag"
                    freezing_plan_details.append(plan_str)

                # Replace name with the concatenated string
                item['name'] = ' | '.join(freezing_plan_details)

            processed_samples.append(item)

        filters['sample'] = processed_samples

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

# If you want to test locally, you can comment out the @login_required decorator
# @login_required
@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    """
    Retrieves details about the grid with pagination and sorting
    :param request: HTTP request
    :return: JSON Format response
    """
    try:
        # Parse and validate query parameters using Pydantic
        query_params = CryoGridsQueryParams(**request.GET.dict())

        # Retrieve filter type
        filter_type = query_params.filter_type

        # Retrieve sorting parameter and direction, make 'sort' and 'asc' optional
        sort_field = query_params.sort  # This will now be 'updated_on' after validation
        if sort_field is None:
            sort_field = 'updated_on'
        # Retrieve asc parameter, default to 'true' (ascending) if not provided
        # Retrieve the asc parameter, default to False (descending)
        asc = query_params.asc
        
        # Determine the sort order based on the asc parameter
        sort_order = sort_field if asc else f'-{sort_field}'  # Default to ascending if not provided

        # Base queryset with consistent ordering
        queryset = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user',
            'grid_cassette', 'freezing_plan'
        ).prefetch_related(
            'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        ).values(
            'id',
            grid_name=F('name'),
            cassette_name=F('grid_cassette__name'),
            project_name=F('intended_project__name'),
            project_id=F('intended_project__id'),
            puck=F('grid_box__puck__name'),
            userID=F('user__id'),
            username=F('user__username'),
            status=F('trashed'),
            created_on=F('create_on'),
            grid_updated_on=F('updated_on'),
            msisession_id=F('msisession__id'),
            msisession_name=F('msisession__name'),
            fz_session_id=F('freezing_session__id'),
            fz_session_datetime=F('freezing_session__datetime'),
            fz_plan_id=F('freezing_plan__id'),
            screening_session_name=F('atlassession__group__name'),
            fz_plan_sample_id=F('freezing_plan__sample__id')
        ).order_by(sort_order)  # Apply sorting based on the provided sort field and direction

        # Apply filters to the queryset
        queryset = apply_filters(queryset, query_params, filter_type)

        # Format the queryset into grid items
        formatted_result = format_queryset_results(queryset)
        # Apply sample name filter if provided
        if query_params.sample_name:
            formatted_result = filter_by_sample_name(formatted_result, query_params.sample_name)
        # Convert the formatted result into a list of grids
        formatted_grid_list = list(formatted_result.values())

        # Apply pagination to the formatted grid list
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)  # Default to 10 items per page if not specified
        paginator = Paginator(formatted_grid_list, page_size)

        try:
            paginated_queryset = paginator.page(page)
        except PageNotAnInteger:
            paginated_queryset = paginator.page(1)
        except EmptyPage:
            paginated_queryset = paginator.page(paginator.num_pages)

        # Check if the paginated result is empty
        if not paginated_queryset.object_list:
            return JsonResponse({'result': []}, status=200)

        # Log the items in the current page
        logger.debug(f'Page {page} items: {paginated_queryset.object_list}')

        # Prepare the response with paginated grids
        response_data = {
            'result': paginated_queryset.object_list,  # Already a list of grids
            'pagination': {
                'page': paginated_queryset.number,
                'page_size': int(page_size),
                'total_pages': paginator.num_pages,
                'total_results': paginator.count,
            }
        }

        response_model = CryoGridResponseModel(
            result=paginated_queryset.object_list,
            pagination=PaginationMetadataModel(
                page=paginated_queryset.number,
                page_size=int(page_size),
                total_pages=paginator.num_pages,
                total_results=paginator.count
            ),
            sort= SortMetadataModel(
                column= 'updatedAt' if sort_field is not None and query_params.sort else None,
                asc= asc
            ),
    )

        return JsonResponse(response_model.dict())

    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

def apply_filters(queryset, query_params, filter_type=None):
    filter_mappings = {
        'project_name': 'intended_project__name__in',
        'cassette_name': 'grid_cassette__name__in',
        'puck_name': 'grid_box__puck__name__in',
        'user_name': 'user__username__in',
        'msi_session_name': 'msisession__name__in',
        'screen_session_name': 'atlassession__group__name__in',
        'trashed': 'trashed__in',
    }

    filters = Q()
    for key, filter_field in filter_mappings.items():
        values = getattr(query_params, key, None)
        if values:
            values = values if isinstance(values, list) else [values]
            if filter_type == 'OR':
                filters |= Q(**{filter_field: values})
            else:  # Default to AND logic
                filters &= Q(**{filter_field: values})
    # Apply the created_on filter based on the month parameter
    if getattr(query_params, 'month', None):
        now = datetime.now()
        start_date = now - timedelta(days=query_params.month * 30)  # Approximate month duration
        filters &= Q(grid_updated_on__gte=start_date)

    return queryset.filter(filters).distinct()


def format_queryset_results(queryset):
    formatted_result = {}
    for item in queryset:
        grid_id = item['id']
        freezing_plan_list = get_freezing_plan_list(item['fz_plan_id'])

        fz_session_datetime_formatted = (
            item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")
            if item['fz_session_datetime'] else None
        )

        if grid_id not in formatted_result:
            formatted_result[grid_id] = {
                'grid': format_grid(item),
                'cassette': {'name': item['cassette_name']},
                'project': format_project(item),
                'puck': {'name': item['puck']},
                'user': {'id': item['userID'], 'name': item['username']},
                'freezingPlan': {'id': item['fz_plan_id'], 'sample': freezing_plan_list},
                'freezingSession': {'id': item['fz_session_id'], 'createdAt': fz_session_datetime_formatted},
                'screeningSession': item['screening_session_name'],
                'msiSession': []
            }

        # Append MSI session details without duplicates
        if item['msisession_id']:
            add_msi_session(formatted_result[grid_id]['msiSession'], item)

    return formatted_result


def get_freezing_plan_list(fz_plan_id):
    try:
        freezing_plan = PlungeFreezingPlan.objects.get(id=fz_plan_id)
        freezing_plan_list = []
        base_url = get_base_url()
        for sample in freezing_plan.sample.all():
            sample_url = f"{base_url}/admin/cryo_grids/sample/{sample.id}"
            tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
            freezing_plan_list.append({
                'id': sample.id,
                'name': f"{sample.name} with {tag_names}" if tag_names else f"{sample.name} without tag",
                'url': sample_url
            })
        return freezing_plan_list
    except ObjectDoesNotExist:
        return []


def format_grid(item):
    base_url = get_base_url()
    grid_url = f"{base_url}/admin/cryo_grids/cryogrid/{item['id']}"
    
    return {
        'id': item['id'],
        'name': f"{item['grid_name']} (id={item['id']})",
        'trashed': item['status'],
        'url': grid_url,
        'createdAt': item['created_on'].isoformat() if item['created_on'] else None,  # Convert datetime to ISO string
        'updatedAt': item['grid_updated_on'].isoformat() if item['grid_updated_on'] else None  # Convert datetime to ISO string
    }


def format_project(item):
    base_url = get_base_url()
    project_url = f"{base_url}/admin/projects/project/{item['project_id']}"
    return {'id': item['project_id'], 'name': item['project_name'], 'url': project_url}

def add_msi_session(msi_session_list, item):
    base_url = get_base_url()
    msi_session_entry = {
        'id': item['msisession_id'],
        'name': item['msisession_name'],
        'url': f"{base_url}/tem/{item['msisession_id']}"
    }
    if msi_session_entry not in msi_session_list:
        msi_session_list.append(msi_session_entry)


def filter_by_sample_name(formatted_result, sample_name_input):
    matching_results = {}

    for grid_id, data in formatted_result.items():
        matching_samples = []

        for sample in data['freezingPlan']['sample']:
            # Check if the sample's full name exactly matches any of the input names
            if sample['name'] in sample_name_input:
                matching_samples.append(sample)

        if matching_samples:
            data['freezingPlan']['sample'] = matching_samples
            matching_results[grid_id] = data

    return matching_results