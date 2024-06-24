from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from cryo_grids.models import CryoGrid, CryoGridBox
from projects.models import Project
from tem.models import MsiSession
from django.db.models import F

def get_grids_by_user(request):
    user_id = request.GET.get('user_id')

    if user_id:
        grids = CryoGrid.objects.filter(user_id=user_id).annotate(
            grid_name=F('name'),
            project_name=F('intended_project__name')  # Using 'intended_project' as the foreign key to Project
        ).values('id', 'grid_name', 'project_name')
    else:
        grids = CryoGrid.objects.annotate(
            grid_name=F('name'),
            project_name=F('intended_project__name')  # Using 'intended_project' as the foreign key to Project
        ).values('id', 'grid_name', 'project_name')

    return JsonResponse(list(grids), safe=False)

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