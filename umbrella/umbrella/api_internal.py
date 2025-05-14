from django.http import JsonResponse
from django.db.models import F
from cryo_grids.models import CryoGrid
from projects.models import Project
from tem.models import MsiSession
from processes.models import Tomograms, Annotation, Pipe, PipeInPlan, ProcPlan, PipeJoint, ProcRun, Review, ReviewTomogram
from django.db.models import F, Case, When, Value, BooleanField
import paramiko
import os
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import datetime
import json
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid

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

@method_decorator(csrf_exempt, name='dispatch')

class ReviewView(View):
    def get(self, request):
        """
        List all review sessions with pagination, search, and sorting.
        """
        # Get pagination parameters
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Get search parameter
        search = request.GET.get('search', '').strip()
        
        # Get sort parameter
        order_by = request.GET.get('orderBy', 'requestedAt:desc')
        sort_field, sort_order = order_by.split(':') if ':' in order_by else ('requestedAt', 'desc')
        
        # Start with base queryset
        queryset = Review.objects.select_related('session', 'requestor').all()
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(review_name__icontains=search) |
                Q(session__name__icontains=search)
            )
        
        # Apply sorting
        if sort_field == 'requestedAt':
            sort_field = 'created_at'
        elif sort_field == 'updatedAt':
            sort_field = 'updated_at'
        
        if sort_order == 'desc':
            queryset = queryset.order_by(f'-{sort_field}')
        else:
            queryset = queryset.order_by(sort_field)
        
        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply pagination
        queryset = queryset[offset:offset + limit]
        
        # Format the response
        reviews_data = []
        for review in queryset:
            # Determine status based on reviewed count
            if review.reviewed_count == 0:
                status = "Not Started"
            elif review.reviewed_count < review.total_count:
                status = "In Progress"
            else:
                status = "Complete"
                
            reviews_data.append({
                "reviewId": str(review.review_id),
                "reviewName": review.review_name,
                "reviewType": review.review_type,
                "sessionId": review.session.name,
                "runId": review.run_id,
                "reconstructionType": review.reconstruction_type,
                "updatedAt": review.updated_at.isoformat(),
                "status": status,
                "reviewedCount": review.reviewed_count,
                "totalCount": review.total_count,
                "reviewer": {
                    "id": str(review.requestor.id) if review.requestor else None,
                    "name": review.requestor.username if review.requestor else None
                }
            })
        
        return JsonResponse({
            "data": reviews_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        }, safe=False)

    def post(self, request):
        """
        Create a new review session from an embrElla sessionId.
        
        Request Body:
        {
            "reviewName": string,               // Display name for review
            "reviewType": "tomogram_quality",   // Enum (e.g., "segmentation_labeling")
            "sessionId": string,                // Selected EmbrElla TEM session ID
            "runId": string,                    // Selected run within the session
            "reconstructionType": string,       // "DCTF" | "Denoised" | "SART"
            "requestor": number                 // User ID creating the review
        }
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
        # Validate required fields
        required_fields = ['reviewName', 'reviewType', 'sessionId', 'runId', 'reconstructionType', 'requestor']
        for field in required_fields:
            if field not in data:
                return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
        
        # Validate reconstruction type
        valid_reconstruction_types = ['DCTF', 'Denoised', 'SART']
        if data['reconstructionType'] not in valid_reconstruction_types:
            return JsonResponse({"error": f"Invalid reconstruction type. Must be one of: {', '.join(valid_reconstruction_types)}"}, status=400)
        
        try:
            # Get the session
            session = MsiSession.objects.get(id=data['sessionId'])
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)
        
        try:
            # Get the requestor user
            requestor = User.objects.get(id=data['requestor'])
        except User.DoesNotExist:
            return JsonResponse({"error": "Requestor user not found"}, status=404)
        
        # Create the review
        try:
            review = Review.objects.create(
                review_name=data['reviewName'],
                review_type=data['reviewType'],
                run_id=data['runId'],
                reconstruction_type=data['reconstructionType'],
                session=session,
                requestor=requestor,  # Use the User instance we just fetched
                status='not_started',
                total_count=0,  # Will be updated when tomograms are added
                reviewed_count=0
            )
            
            # Return the created review
            return JsonResponse({
                "reviewId": str(review.review_id),
                "sessionId": review.session.name,
                "runId": review.run_id,
                "reconstructionType": review.reconstruction_type,
                "reviewName": review.review_name,
                "totalCount": review.total_count,
                "status": "not_started",
                "createdAt": review.created_at.isoformat()
            }, status=201)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

def export_review_results(request, review_id):
    """
    Export final review annotations after completion.
    
    Args:
        request: HTTP request
        review_id: UUID of the review to export
    
    Returns:
        JSON file containing the review annotations
    """
    print(f"Looking for review with ID: {review_id}")
    print(f"Type of review_id: {type(review_id)}")
    
    try:
        # Convert string to UUID if needed
        if isinstance(review_id, str):
            try:
                review_id = uuid.UUID(review_id)
                print(f"Converted to UUID: {review_id}")
            except ValueError as e:
                print(f"UUID conversion error: {str(e)}")
                return JsonResponse({"error": "Invalid review ID format"}, status=400)
        
        # Get the review
        print(f"Querying database with UUID: {review_id}")
        review = Review.objects.get(review_id=review_id)
        print(f"Found review: {review}")
        print(f"Review ID: {review.review_id}")
        print(f"Review Name: {review.review_name}")
        print(f"Review Status: {review.status}")
    except Review.DoesNotExist:
        print(f"No review found with ID: {review_id}")
        # List all available review IDs for debugging
        all_reviews = Review.objects.all()
        print("Available review IDs:")
        for r in all_reviews:
            print(f"- {r.review_id} (Name: {r.review_name}, Status: {r.status})")
        return JsonResponse({"error": "Review not found"}, status=404)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    
    # Check if review is completed
    if review.status != 'completed':
        return JsonResponse({"error": "Review must be completed before exporting"}, status=400)
    
    # Check if save_path exists
    if not review.save_path:
        return JsonResponse({"error": "No saved annotations found for this review"}, status=404)
    
    try:
        # Read the saved JSON file
        with open(review.save_path, 'r') as f:
            annotations_data = json.load(f)
        
        # Create the response with the JSON file
        response = JsonResponse(annotations_data)
        
        # Set headers for file download
        filename = f"review_{review_id}_export.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/json'
        
        return response
        
    except FileNotFoundError:
        return JsonResponse({"error": "Annotation file not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid annotation file format"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

