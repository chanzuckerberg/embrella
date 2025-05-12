from django.http import JsonResponse
from django.db.models import F
from cryo_grids.models import CryoGrid
from projects.models import Project
from tem.models import MsiSession
from processes.models import Tomograms, Annotation, Pipe, PipeInPlan, ProcPlan, PipeJoint, ProcRun
from django.db.models import F, Case, When, Value, BooleanField
import paramiko
import os

HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')

def get_grids_by_user(request):
    user_id = request.GET.get('user_id')
    
    # Annotate each grid with an is_default flag based on the grid name.
    queryset = CryoGrid.objects.select_related('intended_project', 'user').annotate(
        project_name=F('intended_project__name'),
        username=F('user__username'),
        is_default=Case(
            When(name__icontains="default grid", then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # Order by create_on in descending order (newest first)get_tomoget_tomo
    queryset = queryset.order_by('-create_on')
    
    # Return the data including the computed is_default field
    grids = queryset.values('id', 'name', 'project_name', 'username', 'is_default', 'create_on')
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
                "grid_specimen": grid.specimen.__str__(),
                "grid_slot_number": grid.slot_number_in_cassette,
                "grid_project_name": grid.intended_project.name,
            })

        return JsonResponse(grids_data, safe=False)
    else:
        return JsonResponse({"error": "Cassette ID not provided."}, status=400)

def _get_data_by_msi_session_data_type(plan, session, data_types=[]):
        # Find the first pipe in the plan
        valid_pipes_in_plan = PipeInPlan.objects.filter(plan=plan, step=1).distinct()
        if len(valid_pipes_in_plan) > 1:
            raise ValueError("Plan can only have one first pipe.")
        # Get the available tomogram for the given session and plan input pipe
        valid_pipes = []
        for vpp in valid_pipes_in_plan:
            my_pipe = vpp.pipe
            # filter data_types as the right input_pipe
            input_joints = PipeJoint.objects.filter(pipe_in_plan__pipe=my_pipe,input_pathtype__static_path__data_type__in=data_types)
            if not input_joints:
                continue
            # there should always be only one
            valid_pipes.append(input_joints[0].input_pipe_in_plan.pipe)
        return valid_pipes

def get_tomo_by_msi_session(request):
    """
    Return form selector options as json response of Tomograms
    that belong to the session and are valid as the input of the first pipe in the plan.
    """
    plan_id = request.GET.get('plan_id')
    session_id = request.GET.get('session_id')
    run_number = request.GET.get('run_number')
    if not plan_id:
        return JsonResponse({"error": "Processing Plan ID not provided."}, status=400)
    else:
        # Ensure session_id is valid
        try:
            plan = ProcPlan.objects.get(id=plan_id)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "Processing Plan not found."}, status=404)
    if not session_id:
        return JsonResponse({"error": "MsiSession ID not provided."}, status=400)
    else:
        # Ensure session_id is valid
        try:
            session = MsiSession.objects.get(id=session_id)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "MsiSession not found."}, status=404)
    # tomo
    try:
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=['rec','deno'])
    except Exception as e:
        return JsonResponse({"error": e }, status=404)

    input_tomos = []
    for valid_pipe in valid_pipes:
        tomo = Tomograms.objects.filter(
            msi_session=session, pipe_data__pipe=valid_pipe
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            tomo = tomo.filter(pipe_data__run__name=run_number)
        tomo = tomo.distinct()
        input_tomos.extend(list(tomo))
    tomo_data = []
    for tomo in input_tomos:
        tomo_data.append({
            "id": tomo.id,
            "name": tomo.pipe_data.__str__(),
        })

    try:
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=['pick'])
    except Exception as e:
        return JsonResponse({"error": e }, status=404)
    if not valid_pipes:
        return JsonResponse([tomo_data, []], safe=False)
    input_picks = []
    for valid_pipe in valid_pipes:
        pick = Annotation.objects.filter(
            msi_session=session, pipe_data__pipe=valid_pipe, annotation_type='point'
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            pick = pick.filter(pipe_data__run__name=run_number)
        pick = pick.distinct()
        input_picks.extend(list(pick))
    pick_data = []
    for pick in input_picks:
        pick_data.append({
            "id": pick.id,
            "name": pick.pipe_data.__str__(),
        })

    return JsonResponse([tomo_data, pick_data], safe=False)

from django.db.models import Q
from django.http import JsonResponse

def fetch_session_names(request):
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))
    search = request.GET.get("search", "").strip()

    sessions_qs = MsiSession.objects.all().order_by('-created_at')
    if search:
        sessions_qs = sessions_qs.filter(Q(name__icontains=search))

    # Get total count before pagination
    total_count = sessions_qs.count()
    sessions = sessions_qs[offset:offset + limit]

    aretomo3_overlay_path = "/hpc/projects/krios1.processing/aretomo3"
    denoise_overlay_path = "/hpc/projects/krios1.processing/denoise"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh_config = {
        'hostname': HOST,
        'port': PORT,
        'username': USERNAME,
        'password': PASSWORD,
        'timeout': 10,
        'allow_agent': False,
        'look_for_keys': False,
        'compress': True,
        'banner_timeout': 10
    }

    try:
        ssh.connect(**ssh_config)
        sftp = ssh.open_sftp()
        sessions_data = []

        for session in sessions:
            session_runs = []

            # ARETOMO3 directory
            aretomo_session_path = f"{aretomo3_overlay_path}/{session.name}"
            try:
                run_folders = [
                    f.filename for f in sftp.listdir_attr(aretomo_session_path)
                    if f.filename.startswith('run') and f.filename[3:].isdigit()
                ]

                for run_folder in sorted(run_folders):
                    run_path = f"{aretomo_session_path}/{run_folder}"
                    try:
                        file_list = sftp.listdir(run_path)
                        num_tomograms = len([
                            f for f in file_list
                            if f.endswith('.mrc') and not f.endswith('_CTF.mrc') and not f.endswith('_Vol.mrc')
                        ])
                        session_runs.append({
                            "runId": run_folder,
                            "numTomograms": num_tomograms,
                            "reconstructionTypes": ["DCTF", "SART"]
                        })
                    except IOError:
                        continue
            except IOError:
                pass

            # DENOISE directory
            denoise_session_path = f"{denoise_overlay_path}/{session.name}"
            try:
                run_folders = [
                    f.filename for f in sftp.listdir_attr(denoise_session_path)
                    if f.filename.startswith('run') and f.filename[3:].isdigit()
                ]

                for run_folder in sorted(run_folders):
                    run_path = f"{denoise_session_path}/{run_folder}"
                    try:
                        file_list = sftp.listdir(run_path)
                        num_tomograms = len([
                            f for f in file_list
                            if f.endswith('.mrc') and not f.endswith('_CTF.mrc')
                        ])
                        session_runs.append({
                            "runId": run_folder,
                            "numTomograms": num_tomograms,
                            "reconstructionTypes": ["Denoised"]
                        })
                    except IOError:
                        continue
            except IOError:
                pass

            sessions_data.append({
                "sessionId": str(session.id),
                "sessionName": session.name,
                "createdAt": session.created_at.isoformat() if session.created_at else None,
                "runs": session_runs
            })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        try:
            ssh.close()
        except Exception:
            pass

    return JsonResponse({
        "data": sessions_data,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    }, safe=False)