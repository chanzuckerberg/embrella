from django.shortcuts import render
from django.http import JsonResponse
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, Puck, CryoGridCassette, \
    PlungeFreezingSession, PlungeFreezingPlan
from projects.models import Project
from tem.models import MsiSession
from django.contrib.auth.models import User
from django.db.models import F
from django.http import JsonResponse
from .models import CryoGridBox, CryoGrid
from django.views.decorators.http import require_http_methods
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.db.models import F, Q, Count
from django.core.exceptions import ObjectDoesNotExist, ValidationError


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


from django.http import JsonResponse
from .models import CryoGrid, CryoGridBox
from django.contrib.auth.decorators import login_required


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


@require_http_methods(["GET"])
def available_filters(request):
    try:
        # Base queryset with annotations for counting occurrences
        queryset = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user',
            'grid_cassette', 'freezing_plan'
        ).prefetch_related(
            'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        )

        # Aggregating counts for each filter
        filters = {
            'project': queryset.values(project_name=F('intended_project__name'))
                               .annotate(count=Count('id'))
                               .order_by('project_name'),
            'puck': queryset.values(puck_name=F('grid_box__puck__name'))
                            .annotate(count=Count('id'))
                            .order_by('puck_name'),
            'sample': queryset.values(sample_name=F('freezing_plan__sample__name'))
                              .annotate(count=Count('id'))
                              .order_by('sample_name'),
            'username': queryset.values(username=F('user__username'))
                                .annotate(count=Count('id'))
                                .order_by('username'),
            'cassette': queryset.values(cassette_name=F('grid_cassette__name'))
                                .annotate(count=Count('id'))
                                .order_by('cassette_name'),
            'screen_session': queryset.values(screen_session_name=F('atlassession__group__name'))
                                       .annotate(count=Count('id'))
                                       .order_by('screen_session_name'),
            'msi_session': queryset.values(msi_session_name=F('msisession__name'))
                                    .annotate(count=Count('id'))
                                    .order_by('msi_session_name'),
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

        # Convert to the expected output format
        response_data = {
            "filters": {key: list(value) for key, value in filters.items()}
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_cryo_grids_details2(request):
    # Retrieve all input parameters
    input_params = {
        'project_name': request.GET.get('project_name'),
        'cassette_name': request.GET.get('cassette_name'),
        'grid_name': request.GET.get('grid_name'),
        'puck_name': request.GET.get('puck_name'),
        'user_name': request.GET.get('user_name'),
        'sample_name': request.GET.get('sample_name'),
        'msi_session_name': request.GET.get('msi_session_name'),
        'screen_session_name': request.GET.get('screen_session_name')
    }

    # Process input_user_name to handle firstname.lastname format
    if input_params['user_name']:
        input_params['user_name'] = input_params['user_name'].split('@')[0]

    # Validate input parameters
    for key, value in input_params.items():
        if value is not None and not isinstance(value, str):
            return JsonResponse({'error': f'Invalid {key} parameter type, expected string.'}, status=422)

    try:
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
            screening_session_name=F('atlassession__group__name')
        )

        # Apply filters based on input parameters
        filter_mappings = {
            'project_name': 'intended_project__name',
            'cassette_name': 'grid_cassette__name',
            'grid_name': 'name',
            'puck_name': 'grid_box__puck__name',
            'user_name': 'user__username__icontains',
            'sample_name': 'freezing_plan__sample__name__icontains',
            'msi_session_name': 'msisession__name__icontains',
            'screen_session_name': 'atlassession__group__name__icontains',
        }

        for key, filter_field in filter_mappings.items():
            value = input_params.get(key)
            if value:
                queryset = queryset.filter(**{filter_field: value})
                if not queryset.exists():
                    return JsonResponse({'error': f'No grid found with the {key.replace("_", " ")}: {value}'}, status=404)

        formatted_result = {}

        for item in queryset:
            grid_id = item['id']

            # Format datetime field if it exists
            fz_session_datetime_formatted = (
                item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")
                if item['fz_session_datetime'] else None
            )

            # Fetching freezing plan sample and tag details
            freezing_plan_list = []
            try:
                freezing_plan = PlungeFreezingPlan.objects.get(id=item['fz_plan_id'])
                for sample_name in freezing_plan.sample.values_list('name', flat=True):
                    tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
                    plan_str = f"{sample_name} with {tag_names}" if tag_names else f"{sample_name} without tag"
                    freezing_plan_list.append(plan_str)
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Related freezing plan not found.'}, status=404)
            except ValidationError as e:
                return JsonResponse({'error': f'Validation error: {str(e)}'}, status=422)

            if grid_id not in formatted_result:
                grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{grid_id}"
                project_url = f"http://umbrella.czbiohub.org/admin/projects/project/{item['project_id']}"

                formatted_result[grid_id] = {
                    'grid': {
                        'id': grid_id,
                        'name': f"{item['grid_name']} (id={grid_id})",
                        'trashed': item['status'],
                        'url': grid_url,
                        'created_at': item['created_on'],
                    },
                    'cassette': {
                        'name': item['cassette_name'],
                    },
                    'project': {
                        'id': item['project_id'],
                        'name': item['project_name'],
                        'url': project_url
                    },
                    'puck': {
                        'name': item['puck']
                    },
                    'user': {
                        'id': item['userID'],
                        'name': item['username']
                    },
                    'freezingPlan': {
                        'id': item['fz_plan_id'],
                        'sample': freezing_plan_list,
                    },
                    'freezingSession': {
                        'id': item['fz_session_id'],
                        'created_at': fz_session_datetime_formatted
                    },
                    'screeningSession': item['screening_session_name'],
                    'msiSession': [],
                }

            # Append MSI session details
            if item['msisession_id']:
                msi_url = f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
                formatted_result[grid_id]['msiSession'].append({
                    'id': item['msisession_id'],
                    'name': item['msisession_name'],
                    'url': msi_url
                })

        formatted_result_list = list(formatted_result.values())

        return JsonResponse({'Result': formatted_result_list})

    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)




@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    # Retrieve all input parameters
    input_params = {
        'project_name': request.GET.get('project_name'),
        'cassette_name': request.GET.get('cassette_name'),
        'grid_name': request.GET.get('grid_name'),
        'puck_name': request.GET.get('puck_name'),
        'user_name': request.GET.get('user_name'),
        'sample_name': request.GET.get('sample_name'),
        'msi_session_name': request.GET.get('msi_session_name'),
        'screen_session_name': request.GET.get('screen_session_name')
    }

    # Retrieve filter type (AND or OR)
    filter_type = request.GET.get('filter_type', 'AND').upper()  # Default to AND if not provided

    # Process input_user_name to handle firstname.lastname format
    if input_params['user_name']:
        input_params['user_name'] = input_params['user_name'].split('@')[0]

    # Validate input parameters
    for key, value in input_params.items():
        if value is not None and not isinstance(value, str):
            return JsonResponse({'error': f'Invalid {key} parameter type, expected string.'}, status=422)

    try:
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
            screening_session_name=F('atlassession__group__name')
        )

        # Apply filters based on input parameters
        filter_mappings = {
            'project_name': 'intended_project__name',
            'cassette_name': 'grid_cassette__name',
            'grid_name': 'name',
            'puck_name': 'grid_box__puck__name',
            'user_name': 'user__username__icontains',
            'sample_name': 'freezing_plan__sample__name__icontains',
            'msi_session_name': 'msisession__name__icontains',
            'screen_session_name': 'atlassession__group__name__icontains',
        }

        filters = Q()
        for key, filter_field in filter_mappings.items():
            value = input_params.get(key)
            if value:
                if filter_type == 'AND':
                    filters &= Q(**{filter_field: value})
                elif filter_type == 'OR':
                    filters |= Q(**{filter_field: value})

        # Apply the constructed filters to the queryset
        queryset = queryset.filter(filters)
        if not queryset.exists():
            return JsonResponse({'error': 'No grid found matching the provided criteria.'}, status=404)

        formatted_result = {}

        for item in queryset:
            grid_id = item['id']

            # Format datetime field if it exists
            fz_session_datetime_formatted = (
                item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")
                if item['fz_session_datetime'] else None
            )

            # Fetching freezing plan sample and tag details
            freezing_plan_list = []
            try:
                freezing_plan = PlungeFreezingPlan.objects.get(id=item['fz_plan_id'])
                for sample_name in freezing_plan.sample.values_list('name', flat=True):
                    tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
                    plan_str = f"{sample_name} with {tag_names}" if tag_names else f"{sample_name} without tag"
                    freezing_plan_list.append(plan_str)
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Related freezing plan not found.'}, status=404)
            except ValidationError as e:
                return JsonResponse({'error': f'Validation error: {str(e)}'}, status=422)

            if grid_id not in formatted_result:
                grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{grid_id}"
                project_url = f"http://umbrella.czbiohub.org/admin/projects/project/{item['project_id']}"

                formatted_result[grid_id] = {
                    'grid': {
                        'id': grid_id,
                        'name': f"{item['grid_name']} (id={grid_id})",
                        'trashed': item['status'],
                        'url': grid_url,
                        'created_at': item['created_on'],
                    },
                    'cassette': {
                        'name': item['cassette_name'],
                    },
                    'project': {
                        'id': item['project_id'],
                        'name': item['project_name'],
                        'url': project_url
                    },
                    'puck': {
                        'name': item['puck']
                    },
                    'user': {
                        'id': item['userID'],
                        'name': item['username']
                    },
                    'freezingPlan': {
                        'id': item['fz_plan_id'],
                        'sample': freezing_plan_list,
                    },
                    'freezingSession': {
                        'id': item['fz_session_id'],
                        'created_at': fz_session_datetime_formatted
                    },
                    'screeningSession': item['screening_session_name'],
                    'msiSession': [],
                }

            # Append MSI session details
            if item['msisession_id']:
                msi_url = f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
                formatted_result[grid_id]['msiSession'].append({
                    'id': item['msisession_id'],
                    'name': item['msisession_name'],
                    'url': msi_url
                })

        formatted_result_list = list(formatted_result.values())

        return JsonResponse({'Result': formatted_result_list})

    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)