from django.http import JsonResponse
from cryo_grids.models import CryoGrid
from projects.models import Project
from django.contrib.auth.models import User  # Assuming the user table is the default User model
from django.db.models import F


def get_grids_by_user(request):
    user_id = request.GET.get('user_id')
    project_id = request.GET.get('project_id')

    if user_id and project_id:
        grids = CryoGrid.objects.filter(user_id=user_id, intended_project_id=project_id).select_related(
            'intended_project').annotate(
            grid_name=F('name'),
            project_name=F('intended_project__name'),
            project_id=F('intended_project__id')
        ).values('id', 'grid_name', 'project_name', 'project_id')

        return JsonResponse(list(grids), safe=False)
    else:
        return JsonResponse({'error': 'Missing user_id or project_id'}, status=400)

def get_available_grids(request):
    project_id = request.GET.get('project_id')

    if project_id:
        # Ensure project_id is valid
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found."}, status=404)

        # Get the available grids for the given project
        available_grids = CryoGrid.objects.filter(
            trashed=False,
            msisession__project=project
        ).select_related('grid_box').distinct()

        # Format the data
        grids_data = []
        for grid in available_grids:
            grids_data.append({
                "grid_id": grid.id,
                "grid_name": grid.name,
                "grid_box_id": grid.grid_box.id,
                "grid_box_name": grid.grid_box.name,
            })

        return JsonResponse(grids_data, safe=False)
    else:
        return JsonResponse({"error": "Project ID not provided."}, status=400)