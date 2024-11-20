from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from pydantic import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, F, Value, CharField, Count
from django.db.models.functions import Substr, StrIndex, Trim
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse

# python library import
from datetime import timedelta
from datetime import datetime
import json
import os
import logging
from functools import reduce

# project app imports
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, Puck, CryoGridCassette, \
    PlungeFreezingSession, PlungeFreezingPlan
from .models import CryoGrid, CryoGridBox
from .utils import CryoGridsQueryParams, QueryParams, CryoGridResponseModel, PaginationMetadataModel, SortMetadataModel, GridModel,MSISessionModel, CassetteModel, ProjectModel, PuckModel, UserModel, FreezingPlanModel, SampleModel, FreezingSessionModel, UnprocessableEntity, PaginationMetadataModel, SortMetadataModel
from .forms import ClearCassetteForm

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


@require_http_methods(["GET"])
def grid_cassetes_view(request):
    # Assuming you have a way to get `data.id`, perhaps from a query parameter or some logic.
    data_id = request.GET.get('id')  # Example way to get data.id, adjust as needed.



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
        # print(query_params)
        # Initialize the selected filters based on the validated query parameters
        selected_filters = {}
        for qf in query_params.q:
            selected_filters[qf.category] = set(qf.value)  # Store as a set for efficient lookup
        print(selected_filters)
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
        # Function to add 'selected' key based on user selection
        def add_selected_status(filter_list, category):
            selected_values = selected_filters.get(category, set())
            # print(selected_values)
            # Check if None is present in the selected values for this category
            if None in selected_values:
                # If None is present, mark all items as selected
                for item in filter_list:
                    if item['name'] is None:
                        item['selected'] = True
                    else:
                        item['selected'] = False
            else:
                # Otherwise, continue the original logic
                for item in filter_list:
                    item_name = item['name']

                    # Check if the selected filter contains booleans or strings
                    if isinstance(item_name, bool):
                        # For boolean comparison (status), check if the item is in selected values
                        item['selected'] = item_name in selected_values
                    elif isinstance(item_name, str):
                        # For string comparison, normalize case and check for match
                        item['selected'] = item_name.strip().lower() in {val.lower() for val in selected_values if isinstance(val, str)}
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
            'screeningSession': list(queryset.filter(freezing_session__isnull=False)
                        .annotate(screen_session_temp_name=F('atlassession__group__name'))
                        .values(screen_session_temp_name=F('screen_session_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('screen_session_temp_name')
                        .values(name=F('screen_session_temp_name'), count=F('count'))),
            'msiSession': list(queryset.filter(msisession__isnull=False)  # Exclude null msisession relations
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

                    processed_samples.append({
                        'name': plan_str,
                        'count': item['count'],  # Retain the original count
                        'selected': False  # Default selected status
                    })


            else:
                # If no 'name' exists, simply append the original item
                processed_samples.append(item)


        filters['sample'] = processed_samples
    
        # Apply 'selected' status to filters
        for key, filter_list in filters.items():
            # print(filter_list)
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
        # Get the 'q' parameter from the request and parse it as JSON if it's present
        raw_q_param = request.GET.get('q', None)
        if raw_q_param:
            try:
                q_param = json.loads(raw_q_param)  # Parse q as a list of dictionaries
            except json.JSONDecodeError as e:
                return JsonResponse({'error': f'Invalid JSON format for q parameter: {str(e)}'}, status=400)
        else:
            q_param = []

        # Combine the 'q' parameter with the rest of the query params into a dictionary
        query_data = request.GET.dict()
        query_data['q'] = q_param  # Replace the 'q' string with the parsed list

        try:
            query_params = CryoGridsQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        # Default sort and asc values
        sort_field = 'updated_on'
        asc = False
        page_size = 10  # Default page size

        # Generic function to extract value from different formats
        def extract_value(value):
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            return value

        # Extract sort, asc, and page_size from q_param if they exist
        for item in q_param:
            if item['category'] == 'sort':
                # Map updatedAt to updated_on
                sort_field = 'updated_on' if extract_value(item['value']) == 'modifiedOn' else extract_value(item['value'])
            elif item['category'] == 'asc':
                asc_value = extract_value(item['value'])
                asc = bool(asc_value) if isinstance(asc_value, bool) else asc_value.lower() == 'true'
            elif item['category'] == 'pageSize':
                try:
                    page_size = int(extract_value(item['value']))  # Ensure page_size is an integer
                except ValueError:
                    return JsonResponse({'error': 'Invalid value for page_size, must be an integer'}, status=400)


        # Construct the sort order based on the extracted values
        sort_order = sort_field if asc else f'-{sort_field}'
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
        ).order_by(sort_order)

        # Apply filters from q parameter
        print(query_params.q)
        queryset = apply_filters(queryset, query_params.q)

        # Format the queryset into grid items
        formatted_result = format_queryset_results(queryset)

        # Convert the formatted result into a list of grids
        formatted_grid_list = list(formatted_result.values())
        
        # Check if sample filtering is requested
        sample_filter = next((item for item in q_param if item['category'] == 'sample'), None)
        if sample_filter:
            sample_name_input = sample_filter['value'] if isinstance(sample_filter['value'], list) else [sample_filter['value']]
            formatted_result = filter_by_sample_name(formatted_result, sample_name_input)

        # Convert the formatted result into a list of grids
        formatted_grid_list = list(formatted_result.values())
        # Apply pagination to the formatted grid list
        # page = q_param.get('page', 1)
        # Extract pagination parameters from q_param
        page_param = next((item for item in q_param if item['category'] == 'page'), None)
        page_size_param = next((item for item in q_param if item['category'] == 'pageSize'), None)

        # Default values if pagination params are not provided
        page = int(page_param['value'][0]) if page_param else 1
        page_size = int(page_size_param['value'][0]) if page_size_param else 10

        paginator = Paginator(formatted_grid_list, page_size)

        try:
            paginated_queryset = paginator.page(page)
            print(paginated_queryset.number)
        except PageNotAnInteger:
            paginated_queryset = paginator.page(1)
        except EmptyPage:
            paginated_queryset = paginator.page(paginator.num_pages)

        # Check if the paginated result is empty
        if not paginated_queryset.object_list:
            return JsonResponse({'result': []}, status=200)

        # Prepare the response with paginated grids
        response_data = {
            'result': paginated_queryset.object_list,
            'pagination': PaginationMetadataModel(
                page= paginated_queryset.number,
                pageSize= int(page_size),
                totalPages= paginator.num_pages,
                totalResults= paginator.count,
            ).model_dump(),
            'sortBy': SortMetadataModel(
                sort= 'updatedAt' if sort_field is not None else None,
                asc= asc
            ).model_dump(),
        }

        return JsonResponse(response_data)
    except UnprocessableEntity as e:
        # Return a 422 response for invalid parameters
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


def apply_filters(queryset, filters):
    """
    Apply filters to a queryset based on a list of filter items.

    Args:
        queryset (QuerySet): The initial queryset to filter.
        filters (list): A list of filter items, where each item is a dict with 'category' and 'value' keys.

    Returns:
        QuerySet: The filtered queryset with distinct results.
    """
    filter_mappings = {
        'project': 'intended_project__name__in',
        'cassette': 'grid_cassette__name__in',
        'puck': 'grid_box__puck__name__in',
        'msiSession': 'msisession__name__in',
        'screeningSession': 'atlassession__group__name__in',
        'status': 'trashed__in',
    }
    
    q_filters = Q()
    filter_type = 'OR'
    # Process filters to determine filter_type and create Q objects
    filter_q_objects = []

    date_mapping = {
        'last_1_month': 1,
        'last_3_months': 3,
        'last_6_months': 6
    }

    for filter_item in filters:
        category = filter_item.get('category')
        values = filter_item.get('value')
        
        if category == 'filterType' and values:
            filter_type = values[0].upper() if isinstance(values, list) else values.upper()
        elif category in filter_mappings:
            field = filter_mappings[category]

            # Handle cases where 'null' is passed as a filter value
            if values is None or (isinstance(values, list) and None in values):
                filter_q_objects.append(Q(**{f"{field.split('__')[0]}__isnull": True}))  # Check for NULL values
            elif values:
                if not isinstance(values, list):
                    values = [values]
                filter_q_objects.append(Q(**{field: values}))
        elif category == 'user' and values:
            # Handle username that could be in email format
            usernames = values if isinstance(values, list) else [values]
            q_username_filters = Q()
            for username in usernames:
                if '@' in username:
                    # Extract the part before '@' for the firstname.lastname format
                    username = username.split('@')[0]
                q_username_filters |= Q(user__username__icontains=username)  # Case-insensitive match for username
            filter_q_objects.append(q_username_filters)
        elif category == 'date' and values:
            # Handle the possible values for the 'date' filter
            date_value = values[0] if isinstance(values, list) else values
            if date_value in date_mapping:
                months = date_mapping[date_value]
                now = datetime.now()
                start_date = now - timedelta(days=months * 30)
                filter_q_objects.append(Q(grid_updated_on__gte=start_date))
            else:
                return JsonResponse({'error': f'Invalid value for date filter: {date_value}'}, status=400)

    # Combine Q objects based on filter_type
    if filter_type == 'OR':
        q_filters = reduce(lambda x, y: x | y, filter_q_objects, Q())
    elif filter_type == 'AND':
        print("hitting", filter_type)
        q_filters = reduce(lambda x, y: x & y, filter_q_objects, Q())

    # Return the filtered queryset with distinct results
    return queryset.filter(q_filters).distinct()

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
                'grid': format_grid(item).model_dump(),
                'cassette': format_cassette(item).model_dump(),
                'project': format_project(item).model_dump(),
                'puck': format_puck(item).model_dump(),
                'user': format_user(item).model_dump(),
                'freezingPlan': format_freezing_plan(item).model_dump(),
                'freezingSession': format_freezing_session(item).model_dump(),
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


def format_grid(item):
    base_url = get_base_url()
    grid_url = f"{base_url}/admin/cryo_grids/cryogrid/{item['id']}"
    
    # Return a GridModel instance
    return GridModel(
        id=item['id'],
        name=f"{item['grid_name']} (id={item['id']})",
        trashed=item['status'],
        url=grid_url,
        createdAt=item['created_on'].isoformat() if item['created_on'] else None,  # Convert datetime to ISO string
        updatedAt=item['grid_updated_on'].isoformat() if item['grid_updated_on'] else None  # Convert datetime to ISO string
    )

def format_cassette(item):
    return CassetteModel(name=item['cassette_name'])

def format_project(item):
    base_url = get_base_url()
    project_url = f"{base_url}/admin/projects/project/{item['project_id']}"
    return ProjectModel(id=item['project_id'], name=item['project_name'], url=project_url)

def format_puck(item):
    return PuckModel(name=item['puck'])

def format_user(item):
    return UserModel(id=item['userID'], name=item['username'].split('@')[0] if '@' in item['username'] else item['username'])


def format_freezing_plan(item):
    return FreezingPlanModel(id=item['fz_plan_id'], sample=get_freezing_plan_list(item['fz_plan_id']))

def format_freezing_session(item):
    return FreezingSessionModel(id=item['fz_session_id'], createdAt=str(item['fz_session_datetime']))

def add_msi_session(msi_session_list, item):
    base_url = get_base_url()
    msi_session_entry = MSISessionModel(
        id=item['msisession_id'],
        name=item['msisession_name'],
        url=f"{base_url}/tem/{item['msisession_id']}"
    ).model_dump()
    if msi_session_entry not in msi_session_list:
        msi_session_list.append(msi_session_entry)


def clear_cassette_view(request,error_msg=''):
    '''
    Starting view that renders the form to select the cassette to clear its grids.
    '''
    if request.method == 'POST':
        cassette_id = request.POST['cassette']
        return HttpResponseRedirect(reverse('cryo_grids:clear_cassette_filter', args=(cassette_id,)))
    else:
        form = ClearCassetteForm()
        return render(request, "cryo_grids/clear_cassette.html", {"form": form})

def clear_cassette_filter(request, cassette_id, error_msg=''):
    """
    process and render the page for selecting where the grids will be moved to
    after taken out of the cassette.
    """
    cassette = CryoGridCassette.objects.get(id=cassette_id)
    grids = CryoGrid.objects.filter(grid_cassette=cassette)
    context = {'cassette': cassette, 'grids': grids}
    return render(request, "cryo_grids/clear_cassette_move.html", context)

@require_http_methods(["POST"])
def clear_cassette_move(request, error_msg=''):
    """
    process the action of clearing cassette and move the grids.
    When finished, render the cassette filter page again which should be empty.
    """
    if request.method == 'POST':
        
        for k in request.POST.keys():
            if '_move' in k:
                grid_id = int(k.split('_')[0])
                value = request.POST[k]
                grid = CryoGrid.objects.get(id=grid_id)
                cassette_id = grid.grid_cassette.pk
                grid.grid_cassette = None
                if value.endswith('trash'):
                    setattr(grid, 'grid_box',None)
                    setattr(grid, 'trashed',True)
                grid.save()
        return HttpResponseRedirect(reverse('cryo_grids:clear_cassette_filter', args=(cassette_id,)))
