from django.shortcuts import render
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, Puck, CryoGridCassette, \
    PlungeFreezingSession, PlungeFreezingPlan
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .utils import CryoGridsQueryParams
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, F, Value, CharField, Count
from django.db.models.functions import Substr, StrIndex, Trim
from django.utils.timezone import now
from datetime import timedelta
from django.http import JsonResponse
from .models import CryoGrid, CryoGridBox

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





# @require_http_methods(["GET"])
# def available_filters(request):
#     try:
#         # Base queryset with annotations for counting occurrences
#         queryset = CryoGrid.objects.select_related(
#             'intended_project', 'freezing_session', 'grid_box__puck', 'user',
#             'grid_cassette', 'freezing_plan'
#         ).prefetch_related(
#             'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
#             'atlassession__group'
#         )
#
#         # Calculate the date ranges based on UTC time
#         current_time = now()
#         date_ranges = {
#             'last_1_month': current_time - timedelta(days=30),
#             'last_3_months': current_time - timedelta(days=90),
#             'last_6_months': current_time - timedelta(days=180),
#         }
#
#         # Aggregating counts for each filter
#         filters = {
#             'project': list(queryset.annotate(project_temp_name=F('intended_project__name'))
#                         .values(project_temp_name=F('project_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('project_temp_name')
#                         .values(name=F('project_temp_name'), count=F('count'))),
#             'puck': list(queryset.annotate(puck_temp_name=F('grid_box__puck__name'))
#                         .values(puck_temp_name=F('puck_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('puck_temp_name')
#                         .values(name=F('puck_temp_name'), count=F('count'))),
#             'sample': list(queryset.annotate(sample_temp_name=F('freezing_plan__sample__name'))
#                         .values(sample_temp_name=F('sample_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('sample_temp_name')
#                         .values(name=F('sample_temp_name'), count=F('count'))),
#             'user': list(queryset.annotate(
#                             user_temp_name=Trim(
#                                 Case(
#                                     When(user__username__contains='@',
#                                          then=Substr(F('user__username'), 1, StrIndex(F('user__username'), Value('@')) - 1)),
#                                     default=F('user__username'),
#                                     output_field=CharField()
#                                 )
#                             )
#                         ).values(user_temp_name=F('user_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('user_temp_name')
#                         .values(name=Trim(F('user_temp_name')), count=F('count'))),
#             'cassette': list(queryset.annotate(cassette_temp_name=F('grid_cassette__name'))
#                         .values(cassette_temp_name=F('cassette_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('cassette_temp_name')
#                         .values(name=F('cassette_temp_name'), count=F('count'))),
#             'screeningSession': list(queryset.filter(freezing_session__isnull=False)
#                         .annotate(screen_session_temp_name=F('atlassession__group__name'))
#                         .values(screen_session_temp_name=F('screen_session_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('screen_session_temp_name')
#                         .values(name=F('screen_session_temp_name'), count=F('count'))),
#             'msiSession': list(queryset.filter(msisession__isnull=False)  # Exclude null msisession relations
#                         .annotate(msi_session_temp_name=F('msisession__name'))
#                         .values(msi_session_temp_name=F('msi_session_temp_name'))
#                         .annotate(count=Count('id'))
#                         .order_by('msi_session_temp_name')
#                         .values(name=F('msi_session_temp_name'), count=F('count'))),
#             'status': list(queryset.annotate(status_name=F('trashed'))
#                        .values('status_name')
#                        .annotate(count=Count('id'))
#                        .order_by('trashed')
#                        .values(name=F('status_name'), count=F('count'))),
#             'date': [
#                 {"name": "last_1_month", "count": queryset.filter(create_on__gte=date_ranges['last_1_month']).count()},
#                 {"name": "last_3_months", "count": queryset.filter(create_on__gte=date_ranges['last_3_months']).count()},
#                 {"name": "last_6_months", "count": queryset.filter(create_on__gte=date_ranges['last_6_months']).count()}
#             ]
#         }
#
#         # Process the 'sample' filter and replace sample_name with the detailed information
#         processed_samples = []
#         for item in filters['sample']:
#             if 'name' in item:
#                 # Get the associated freezing plans based on the sample name
#                 freezing_plans = PlungeFreezingPlan.objects.filter(sample__name=item['name'])
#
#                 # Create a string that summarizes the freezing plan details
#                 freezing_plan_details = []
#                 for freezing_plan in freezing_plans:
#                     tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
#                     plan_str = f"{item['name']} with {tag_names}" if tag_names else f"{item['name']} without tag"
#                     freezing_plan_details.append(plan_str)
#
#                 # Replace name with the concatenated string
#                 item['name'] = ' | '.join(freezing_plan_details)
#
#             processed_samples.append(item)
#
#         filters['sample'] = processed_samples
#
#         # Convert to the expected output format
#         response_data = {
#             "filters": filters
#         }
#
#         return JsonResponse(response_data)
#     except Exception as e:
#         return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


# @require_http_methods(["GET"])
# def get_cryo_grids_details(request):
#     try:
#         # Parse and validate query parameters using Pydantic
#         query_params = CryoGridsQueryParams(**request.GET.dict())
#
#         # Retrieve filter type
#         filter_type = query_params.filter_type
#
#         # Base queryset
#         queryset = CryoGrid.objects.select_related(
#             'intended_project', 'freezing_session', 'grid_box__puck', 'user',
#             'grid_cassette', 'freezing_plan'
#         ).prefetch_related(
#             'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
#             'atlassession__group'
#         ).values(
#             'id',
#             grid_name=F('name'),
#             cassette_name=F('grid_cassette__name'),
#             project_name=F('intended_project__name'),
#             project_id=F('intended_project__id'),
#             puck=F('grid_box__puck__name'),
#             userID=F('user__id'),
#             username=F('user__username'),
#             status=F('trashed'),
#             created_on=F('create_on'),
#             msisession_id=F('msisession__id'),
#             msisession_name=F('msisession__name'),
#             fz_session_id=F('freezing_session__id'),
#             fz_session_datetime=F('freezing_session__datetime'),
#             fz_plan_id=F('freezing_plan__id'),
#             screening_session_name=F('atlassession__group__name'),
#             fz_plan_sample_id=F('freezing_plan__sample__id')
#         ).order_by('-created_on')
#
#         filter_mappings = {
#             'project_name': 'intended_project__name__in',
#             'cassette_name': 'grid_cassette__name__in',
#             'grid_name': 'name__in',
#             'puck_name': 'grid_box__puck__name__in',
#             'user_name': 'user__username__in',
#             'msi_session_name': 'msisession__name__in',
#             'screen_session_name': 'atlassession__group__name__in',
#         }
#
#         if filter_type == 'AND':
#             filters = Q()
#             for key, filter_field in filter_mappings.items():
#                 values = getattr(query_params, key)
#                 if values:
#                     if isinstance(values, list):  # if values is a list
#                         filters &= Q(**{filter_field: values})
#                     else:  # if values is a single string
#                         filters &= Q(**{filter_field: [values]})
#             queryset = queryset.filter(filters)
#         elif filter_type == 'OR':
#             initial_queryset = CryoGrid.objects.none()
#             for key, filter_field in filter_mappings.items():
#                 values = getattr(query_params, key)
#                 if values:
#                     if not isinstance(values, list):  # if values is not a list, wrap it in a list
#                         values = [values]
#                     filtered_queryset = queryset.filter(Q(**{filter_field: values}))
#                     initial_queryset = initial_queryset | filtered_queryset
#             queryset = initial_queryset.distinct()
#         # print(queryset)
#         if not queryset.exists():
#             return JsonResponse({'Result': []}, status=200)
#
#         formatted_result = {}
#         for item in queryset:
#             grid_id = item['id']
#
#             # Format datetime field if it exists
#             fz_session_datetime_formatted = (
#                 item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")
#                 if item['fz_session_datetime'] else None
#             )
#
#             # Fetching freezing plan sample and tag details
#             freezing_plan_list = []
#             try:
#                 freezing_plan = PlungeFreezingPlan.objects.get(id=item['fz_plan_id'])
#                 for sample in freezing_plan.sample.all():
#                     sample_id = sample.id
#                     sample_name = sample.name
#                     tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
#                     sample_url = f"http://umbrella.czbiohub.org/admin/samples/{sample_id}"
#                     plan_str = {
#                         'id': sample_id,
#                         'name': f"{sample_name} with {tag_names}" if tag_names else f"{sample_name} without tag",
#                         'url': sample_url
#                     }
#                     freezing_plan_list.append(plan_str)
#             except ObjectDoesNotExist:
#                 return JsonResponse({'error': 'Related freezing plan not found.'}, status=404)
#             except ValidationError as e:
#                 return JsonResponse({'error': f'Validation error: {str(e)}'}, status=422)
#
#             if grid_id not in formatted_result:
#                 grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{grid_id}"
#                 project_url = f"http://umbrella.czbiohub.org/admin/projects/project/{item['project_id']}"
#                 formatted_result[grid_id] = {
#                     'grid': {
#                         'id': grid_id,
#                         'name': f"{item['grid_name']} (id={grid_id})",
#                         'trashed': item['status'],
#                         'url': grid_url,
#                         'createdAt': item['created_on'],
#                     },
#                     'cassette': {
#                         'name': item['cassette_name'],
#                     },
#                     'project': {
#                         'id': item['project_id'],
#                         'name': item['project_name'],
#                         'url': project_url
#                     },
#                     'puck': {
#                         'name': item['puck']
#                     },
#                     'user': {
#                         'id': item['userID'],
#                         'name': item['username']
#                     },
#                     'freezingPlan': {
#                         'id': item['fz_plan_id'],
#                         'sample': freezing_plan_list,
#                     },
#                     'freezingSession': {
#                         'id': item['fz_session_id'],
#                         'createdAt': fz_session_datetime_formatted
#                     },
#                     'screeningSession': item['screening_session_name'],
#                     'msiSession': [],
#                 }
#
#             # Append MSI session details without duplicates
#             if item['msisession_id']:
#                 msi_session_entry = {
#                     'id': item['msisession_id'],
#                     'name': item['msisession_name'],
#                     'url': f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
#                 }
#                 # prevent duplicate
#                 if msi_session_entry not in formatted_result[grid_id]['msiSession']:
#                     formatted_result[grid_id]['msiSession'].append(msi_session_entry)
#
#         # Filter results by sample name if provided
#         if query_params.sample_name:
#             matching_results = {}
#             sample_name_input = query_params.sample_name
#
#             for grid_id, data in formatted_result.items():
#                 sample_list = data['freezingPlan']['sample']
#
#                 # Filter samples within each freezing plan that match any sample_name in the list
#                 matching_samples = [
#                     sample for sample in sample_list
#                     if any(s_name in sample['name'] for s_name in sample_name_input)
#                 ]
#
#                 if matching_samples:
#                     data['freezingPlan']['sample'] = matching_samples
#                     matching_results[grid_id] = data
#
#             formatted_result = matching_results
#
#         formatted_result_list = list(formatted_result.values())
#
#         return JsonResponse({'Result': formatted_result_list})
#
#     except ValidationError as e:
#         return JsonResponse({'error': e.errors()}, status=400)
#     except Exception as e:
#         return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
@require_http_methods(["GET"])
def available_filters(request):
    try:
        # Extract input parameters from the request and split by comma to form a list
        selected_filters = request.GET.get('selected_filters', '').split(',')

        print("Selected Filters:", selected_filters)  # Debugging line

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
        def add_selected_status(filter_list):
            for item in filter_list:
                # Ensure 'name' is a string before checking if it is in selected_filters
                if isinstance(item['name'], str):
                    item['selected'] = item['name'] in selected_filters
                else:
                    item['selected'] = False

        # Aggregating counts for each filter
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
                    freezing_plan_details.append(plan_str)

                # Replace name with the concatenated string
                item['name'] = ' | '.join(freezing_plan_details)

            processed_samples.append(item)

        filters['sample'] = processed_samples

        # Apply 'selected' status to filters
        for key, filter_list in filters.items():
            add_selected_status(filter_list)

        # Convert to the expected output format
        response_data = {
            "filters": filters
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    try:
        # Parse and validate query parameters using Pydantic
        query_params = CryoGridsQueryParams(**request.GET.dict())

        # Retrieve filter type
        filter_type = query_params.filter_type

        # Base queryset
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
            msisession_id=F('msisession__id'),
            msisession_name=F('msisession__name'),
            fz_session_id=F('freezing_session__id'),
            fz_session_datetime=F('freezing_session__datetime'),
            fz_plan_id=F('freezing_plan__id'),
            screening_session_name=F('atlassession__group__name'),
            fz_plan_sample_id=F('freezing_plan__sample__id')
        ).order_by('-created_on')

        queryset = apply_filters(queryset, query_params, filter_type)

        if not queryset.exists():
            return JsonResponse({'result': []}, status=200)
        print(queryset)
        formatted_result = format_queryset_results(queryset)

        # Filter results by sample name if provided
        if query_params.sample_name:
            formatted_result = filter_by_sample_name(formatted_result, query_params.sample_name)

        return JsonResponse({'result': list(formatted_result.values())})

    except Exception as e:
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
        values = getattr(query_params, key)
        if values:
            values = values if isinstance(values, list) else [values]
            filters &= Q(**{filter_field: values})

    # Apply the filters based on the filter type or by default to AND logic
    if filter_type == 'OR':
        queryset = queryset.filter(filters).distinct()
    else:  # Default to AND logic if filter_type is not provided or is AND
        queryset = queryset.filter(filters)

    return queryset

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
        for sample in freezing_plan.sample.all():
            sample_url = f"http://umbrella.czbiohub.org/admin/samples/{sample.id}"
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
    grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{item['id']}"
    return {
        'id': item['id'],
        'name': f"{item['grid_name']} (id={item['id']})",
        'trashed': item['status'],
        'url': grid_url,
        'createdAt': item['created_on'],
    }


def format_project(item):
    project_url = f"http://umbrella.czbiohub.org/admin/projects/project/{item['project_id']}"
    return {'id': item['project_id'], 'name': item['project_name'], 'url': project_url}


def add_msi_session(msi_session_list, item):
    msi_session_entry = {
        'id': item['msisession_id'],
        'name': item['msisession_name'],
        'url': f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
    }
    if msi_session_entry not in msi_session_list:
        msi_session_list.append(msi_session_entry)


def filter_by_sample_name(formatted_result, sample_name_input):
    matching_results = {}
    for grid_id, data in formatted_result.items():
        matching_samples = [
            sample for sample in data['freezingPlan']['sample']
            if any(s_name in sample['name'] for s_name in sample_name_input)
        ]
        if matching_samples:
            data['freezingPlan']['sample'] = matching_samples
            matching_results[grid_id] = data
    return matching_results