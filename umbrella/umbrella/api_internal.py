from django.http import JsonResponse
from django.db.models import F
from cryo_grids.models import CryoGrid
from projects.models import Project
from tem.models import MsiSession
from processes.models import Tomograms, Pipe, PipeInPlan, PipelinePlan


def get_grids_by_user(request):
    user_id = request.GET.get('user_id')

    if user_id:
        grids = CryoGrid.objects.filter(user_id=user_id).select_related('intended_project', 'user').annotate(
            project_name=F('intended_project__name'),
            username=F('user__username')
        ).values('id', 'name', 'project_name', 'username')
    else:
        grids = CryoGrid.objects.select_related('intended_project', 'user').annotate(
            project_name=F('intended_project__name'),
            username=F('user__username')
        ).values('id', 'name', 'project_name', 'username')

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

def get_grids_by_cassette(request):
    cassette_id = request.GET.get('cassette_id')
    if cassette_id:
        grids = CryoGrid.objects.filter(grid_cassette__id=cassette_id)
        # Format the data
        print(grids)
        grids_data = []
        for grid in grids:
            grids_data.append({
                "grid_id": grid.id,
                "grid_user": grid.user.username,
                "grid_name": grid.name,
                "grid_freezing": grid.freezing_plan.__str__(),
                "grid_slot_number": grid.slot_number_in_cassette,
                "grid_project_name": grid.intended_project.name,
            })

        return JsonResponse(grids_data, safe=False)
    else:
        return JsonResponse({"error": "Cassette ID not provided."}, status=400)

def get_tomo_by_msi_session(request):
    """
    Return form selector options as json response of Tomograms
    that belong to the session and are valid as the input of the first pipe in the plan.
    """
    plan_id = request.GET.get('plan_id')
    session_id = request.GET.get('session_id')
    if session_id:
        # Ensure session_id is valid
        try:
            session = MsiSession.objects.get(id=session_id)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "MsiSession not found."}, status=404)

        # Find the first pipe in the plan
        valid_pipes_in_plan = PipeInPlan.objects.filter(plan=PipelinePlan.objects.get(id=plan_id), step=1).distinct()
        if len(valid_pipes_in_plan) > 1:
            return JsonResponse({"error": "Plan can only have one first pipe."}, status=400)
        # Get the available tomogram for the given session and plan input pipe
        input_tomos = []
        for vpp in valid_pipes_in_plan:
            # filter tomo as the right input_pipe
            valid_pipe = vpp.pipe.input_pipe
            tomo = Tomograms.objects.filter(
                msi_session=session, pipe_data__pipe=valid_pipe
            ).distinct()
            input_tomos.extend(list(tomo))
        tomo_data = []
        for tomo in input_tomos:
            tomo_data.append({
                "id": tomo.id,
                "name": tomo.pipe_data.__str__(),
            })

        return JsonResponse(tomo_data, safe=False)
    else:
        return JsonResponse({"error": "MsiSession ID not provided."}, status=400)
