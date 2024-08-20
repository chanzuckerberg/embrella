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


from django.http import JsonResponse
from django.db.models import F, Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError

@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    input_grid_name = request.GET.get('grid_name')
    input_puck_name = request.GET.get('puck_name')
    input_user_name = request.GET.get('user_name')

    # Process input_user_name to handle firstname.lastname format
    if input_user_name:
        input_user_name = input_user_name.split('@')[0]

    # Edge Case: Invalid Query Parameters
    if input_grid_name is not None and not isinstance(input_grid_name, str):
        return JsonResponse({'error': 'Invalid grid_name parameter type, expected string.'}, status=422)
    if input_puck_name is not None and not isinstance(input_puck_name, str):
        return JsonResponse({'error': 'Invalid puck_name parameter type, expected string.'}, status=422)
    if input_user_name is not None and not isinstance(input_user_name, str):
        return JsonResponse({'error': 'Invalid user_name parameter'}, status=422)

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
            screening_session_name=F('atlassession__group__name')  # Getting the name from ScreenSessionGroup
        )

        # Apply filtering if grid_name is provided
        if input_grid_name:
            queryset = queryset.filter(name=input_grid_name)
            if not queryset.exists():
                return JsonResponse({'error': f'No grid found with the name: {input_grid_name}'}, status=404)

        # Apply filtering if puck_name is provided
        if input_puck_name:
            queryset = queryset.filter(grid_box__puck__name=input_puck_name)
            if not queryset.exists():
                return JsonResponse({'error': f'No grid found with the puck name: {input_puck_name}'}, status=404)

        # Apply filtering if user_name is provided
        if input_user_name:
            queryset = queryset.filter(Q(user__username__icontains=input_user_name))
            if not queryset.exists():
                return JsonResponse({'error': f'No grid found with the user name: {input_user_name}'}, status=404)

        result = queryset

        # Reformat the data to match the desired structure
        formatted_result = {}

        for item in result:
            grid_id = item['id']

            # Directly format datetime fields to "yyyy-mm-dd hh:mm" format
            fz_session_datetime_formatted = None
            if item['fz_session_datetime']:
                fz_session_datetime_formatted = item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")

            try:
                # Fetching the freezing plan sample and tag details
                freezing_plan = PlungeFreezingPlan.objects.get(id=item['fz_plan_id'])

                # Creating a list to hold the formatted sample and tag strings
                freezing_plan_list = []

                # Iterate through the sample names
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

            # Append MSI session details to the 'msiSession' list
            if item['msisession_id']:
                msi_url = f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
                formatted_result[grid_id]['msiSession'].append({
                    'id': item['msisession_id'],
                    'name': item['msisession_name'],
                    'url': msi_url
                })

        # Convert the formatted_result dictionary to a list
        formatted_result_list = list(formatted_result.values())

        return JsonResponse({'Result': formatted_result_list})

    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)