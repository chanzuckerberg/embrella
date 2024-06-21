from django.shortcuts import render
from django.http import JsonResponse
from cryo_grids.models import CryoGrid, CryoGridBox
from django.contrib.auth.models import User

from django.views.decorators.http import require_http_methods


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


from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import CryoGridBox, CryoGrid

from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import CryoGridBox, CryoGrid

def get_specific_grids(request):
    grid_box_name = request.GET.get('grid_box_name')

    if grid_box_name:
        try:
            # Find the grid box with the specified name
            grid_box = CryoGridBox.objects.get(name=grid_box_name)

            # Find the grids associated with this grid box and join with the User table
            specific_grids = CryoGrid.objects.filter(grid_box=grid_box).select_related('grid_box', 'user').values(
                'id', 'create_on', 'name', 'notes', 'position_in_box', 'grid_box_id',
                'clipped', 'trashed',#'freezing_plan_id',  #'freezing_session_id',
                'slot_number_in_cassette', 'grid_cassette_id',
                'user__username',
            )

            # Format the data
            grids_data = list(specific_grids)

            return JsonResponse(grids_data, safe=False)
        except CryoGridBox.DoesNotExist:
            return JsonResponse({"error": "Grid box not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Grid box name not provided."}, status=400)