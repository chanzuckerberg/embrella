from django.shortcuts import render
from django.http import JsonResponse
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, PlungeFreezingSession, Puck, CryoGridCassette, PlungeFreezingSession
from projects.models import Project
from tem.models import MsiSession
from django.contrib.auth.models import User
from django.db.models import F
from django.http import JsonResponse
from .models import CryoGridBox, CryoGrid
from django.views.decorators.http import require_http_methods
from datetime import datetime

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
def get_cryo_grids_details(request):

    input_grid_name = request.GET.get('grid_name')
    if input_grid_name:
        pass
    else:
        result = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user', 'grid_cassette'
        ).prefetch_related('msisession').values(
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
            fz_session_datetime=F('freezing_session__datetime')
        )

        # Reformat the data to match the desired structure
        formatted_result = {}

        for item in result:
            grid_id = item['id']


            # Directly format datetime fields to "yyyy-mm-dd hh:mm" format
            created_on_formatted = item['created_on'].strftime("%Y-%m-%d %H:%M")
            fz_session_datetime_formatted = None
            if item['fz_session_datetime']:
                fz_session_datetime_formatted = item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")


            if grid_id not in formatted_result:
                grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{grid_id}"
                project_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/project/{item['project_id']}"

                formatted_result[grid_id] = {
                    'grid': {
                        'id': grid_id,
                        'name': item['grid_name'],
                        'trashed': item['status'],
                        'url': grid_url,
                        'created': item['created_on'],
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
                        'id': None,
                        'sample': None,
                    },
                    'freezingSession': {
                        'id': item['fz_session_id'],
                        'created_at': fz_session_datetime_formatted
                    },
                    'screeningSession': None,
                    'msiSession': []
                }

            # Append MSI session details to the 'msiSession' list
            if item['msisession_id']:
                msi_url = f"http://umbrella.czbiohub.org/admin/tem/msisession/{item['msisession_id']}"
                formatted_result[grid_id]['msiSession'].append({
                    'id': item['msisession_id'],
                    'name': item['msisession_name'],
                    'url': msi_url
                })

        # Convert the formatted_result dictionary to a list
        formatted_result_list = list(formatted_result.values())

        return JsonResponse({'Result': formatted_result_list})