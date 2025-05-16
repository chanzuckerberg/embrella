from django.http import JsonResponse
from django.db.models import F
from cryo_grids.models import CryoGrid
from projects.models import Project
from tem.models import MsiSession
from processes.models import Tomograms, Annotation, Pipe, PipeInPlan, ProcPlan, PipeJoint, ProcRun, Review, ReviewTomogram
from django.db.models import F, Case, When, Value, BooleanField
import paramiko
import os
import socket
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import datetime
import json
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
from django.conf import settings
import os.path

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
    
    try:
        ssh.connect(
            hostname=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
            compress=True,
            banner_timeout=10
        )
        sessions_data = []

        for session in sessions:
            session_name = session.name
            session_runs = {}

            # Use find command to get all .mrc files in one go
            find_cmd = f"""
            find {aretomo3_overlay_path}/{session_name} {denoise_overlay_path}/{session_name} -type f -name "*.mrc" 2>/dev/null | 
            grep -v "_CTF.mrc" | grep -v "_Vol.mrc" | 
            sed -E 's|.*/(run[0-9]+)/.*|\\1|' | sort -u
            """
            
            stdin, stdout, stderr = ssh.exec_command(find_cmd)
            run_folders = [line.strip() for line in stdout if line.strip()]
            
            if not run_folders:
                continue

            # Get tomogram counts and types for each run
            for run_folder in run_folders:
                count_cmd = f"""
                find {aretomo3_overlay_path}/{session_name}/{run_folder} -type f -name "*.mrc" 2>/dev/null | 
                grep -v "_CTF.mrc" | grep -v "_Vol.mrc" | wc -l;
                find {denoise_overlay_path}/{session_name}/{run_folder} -type f -name "*.mrc" 2>/dev/null | 
                grep -v "_CTF.mrc" | wc -l
                """
                
                stdin, stdout, stderr = ssh.exec_command(count_cmd)
                lines = [line.strip() for line in stdout if line.strip()]
                
                reconstruction_types = []
                num_tomograms = 0
                
                if len(lines) >= 2:
                    aretomo_count = int(lines[0])
                    denoise_count = int(lines[1])
                    
                    if aretomo_count > 0:
                        reconstruction_types.extend(['DCTF', 'SART'])
                        num_tomograms = max(num_tomograms, aretomo_count)
                    
                    if denoise_count > 0:
                        reconstruction_types.append('Denoised')
                        num_tomograms = max(num_tomograms, denoise_count)
                
                if reconstruction_types:
                    session_runs[run_folder] = {
                        "runId": run_folder,
                        "numTomograms": num_tomograms,
                        "reconstructionTypes": reconstruction_types
                    }

            sessions_data.append({
                "sessionId": str(session.id),
                "sessionName": session_name,
                "createdAt": session.created_at.isoformat() if session.created_at else None,
                "runs": list(session_runs.values())
            })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
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

def get_session_runs(request, session_id):
    """
    Get all runs and their reconstruction types for a specific session with minimal SSH overhead.
    """
    try:
        session = MsiSession.objects.get(name=session_id)
    except MsiSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    runs = ProcRun.objects.filter(msi_session=session).distinct().values('name')
    runs_data = []

    try:
        # ✅ Open ONE SSH + SFTP connection for all path checks
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
            compress=True,
            banner_timeout=10
        )
        sftp = ssh.open_sftp()
        try:
            # 🔧 Increase buffer sizes
            try:
                sftp.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                sftp.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
            except Exception:
                pass  # If socket options fail, continue normally

            # 🧠 Loop through runs with one SFTP session
            for run in runs:
                run_id = run['name']
                reconstruction_types = []

                # Check aretomo path
                aretomo_path = f"/hpc/projects/krios1.processing/aretomo3/{session_id}/{run_id}"
                try:
                    aretomo_files = sftp.listdir(aretomo_path)
                    if any(f.endswith('.mrc') and not f.endswith('_CTF.mrc') and not f.endswith('_Vol.mrc') for f in aretomo_files):
                        reconstruction_types.extend(['DCTF', 'SART'])
                except IOError:
                    pass

                # Check denoise path
                denoise_path = f"/hpc/projects/krios1.processing/denoise/{session_id}/{run_id}"
                try:
                    denoise_files = sftp.listdir(denoise_path)
                    if any(f.endswith('.mrc') and not f.endswith('_CTF.mrc') for f in denoise_files):
                        reconstruction_types.append('Denoised')
                except IOError:
                    pass

                if reconstruction_types:
                    runs_data.append({
                        "runId": run_id,
                        "reconstructionTypes": reconstruction_types
                    })

        finally:
            sftp.close()
            ssh.close()

    except Exception as e:
        return JsonResponse({"error": f"SSH connection error: {str(e)}"}, status=500)

    return JsonResponse({
        "sessionId": session_id,
        "runs": runs_data
    }, safe=False)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewView(View):
    def get(self, request, review_id=None):
        """
        If review_id is provided, get detailed metadata for a specific review.
        Otherwise, list all review sessions with pagination, search, and sorting.
        """
        if review_id:
            return self.get_review_metadata(request, review_id)
            
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

    def get_review_metadata(self, request, review_id):
        """
        Get detailed metadata for a specific review.
        
        Args:
            request: HTTP request
            review_id: UUID of the review
            
        Returns:
            JSON object with review metadata:
            {
                "reviewId": UUID,
                "reviewName": string,
                "owner": {
                    "id": UUID,
                    "name": string
                },
                "tomograms": [
                    {
                        "tomogramId": string,
                        "status": "pending" | "accepted" | "rejected" | "uncertain"
                    }
                ]
            }
        """
        try:
            # Convert string to UUID if needed
            if isinstance(review_id, str):
                try:
                    review_id = uuid.UUID(review_id)
                except ValueError:
                    return JsonResponse({"error": "Invalid review ID format"}, status=400)
            
            # Get the review with related data
            review = Review.objects.select_related('requestor').get(review_id=review_id)
            
            # Get all tomograms for this review
            tomograms = ReviewTomogram.objects.filter(review=review).values('tomogram_id', 'quality')
            
            # Format the response
            response_data = {
                "reviewId": str(review.review_id),
                "reviewName": review.review_name,
                "owner": {
                    "id": str(review.requestor.id) if review.requestor else None,
                    "name": review.requestor.username if review.requestor else None
                },
                "tomograms": [
                    {
                        "tomogramId": tomo['tomogram_id'],
                        "status": tomo['quality'] if tomo['quality'] else 'pending'
                    }
                    for tomo in tomograms
                ]
            }
            
            return JsonResponse(response_data)
            
        except Review.DoesNotExist:
            return JsonResponse({"error": "Review not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, review_id=None):
        """
        Handle POST requests for both review creation and saving review results.
        
        If review_id is provided, check the URL path to determine the action:
        - /save/ -> save review results
        - /complete/ -> mark review as completed
        Otherwise, create a new review.
        """
        if review_id:
            # Check the URL path to determine the action
            if request.path.endswith('/save/'):
                return self.save_review(request, review_id)
            elif request.path.endswith('/complete/'):
                return self.complete_review(request, review_id)
            else:
                return JsonResponse({"error": "Invalid endpoint"}, status=400)
            
        # Original review creation logic
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
                requestor=requestor,
                status='not_started',
                total_count=0,
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

    def save_review(self, request, review_id):
        """
        Save review results for a specific review.
        
        Args:
            request: HTTP request
            review_id: UUID of the review
            
        Request Body:
        {
            "reviewId": string,
            "sessionId": string (optional),
            "savePath": string,
            "annotations": [
                {
                    "tomogramId": string,
                    "quality": "accepted" | "rejected" | "uncertain",
                    "rejectionReasons": string[] (optional),
                    "objectLabels": string[] (optional)
                }
            ]
        }
        
        Returns:
        {
            "ok": true,
            "savedAt": string (ISO timestamp),
            "savePath": string,
            "reviewedCount": number,
            "totalCount": number
        }
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
            
            # Validate required fields
            required_fields = ['reviewId', 'savePath', 'annotations']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
            
            # Validate review ID matches URL parameter
            if data['reviewId'] != review_id:
                return JsonResponse({"error": "Review ID in request body does not match URL parameter"}, status=400)
            
            # Convert string to UUID if needed
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)
            
            # Get the review
            try:
                review = Review.objects.get(review_id=review_id)
            except Review.DoesNotExist:
                return JsonResponse({"error": "Review not found"}, status=404)
            
            # Validate annotations
            valid_qualities = ['accepted', 'rejected', 'uncertain']
            for annotation in data['annotations']:
                if 'tomogramId' not in annotation or 'quality' not in annotation:
                    return JsonResponse({"error": "Each annotation must have tomogramId and quality"}, status=400)
                if annotation['quality'] not in valid_qualities:
                    return JsonResponse({"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400)
                if annotation['quality'] == 'rejected' and not annotation.get('rejectionReasons'):
                    return JsonResponse({"error": "Rejection reasons are required when quality is rejected"}, status=400)
            
            # Update tomogram reviews
            for annotation in data['annotations']:
                try:
                    tomogram = ReviewTomogram.objects.get(
                        review=review,
                        tomogram_id=annotation['tomogramId']
                    )
                    
                    # Update tomogram review data
                    tomogram.quality = annotation['quality']
                    
                    # Handle rejection reasons
                    if annotation['quality'] == 'rejected':
                        tomogram.rejection_reasons = json.dumps(annotation['rejectionReasons'])
                    else:
                        tomogram.rejection_reasons = json.dumps([])  # Empty array instead of None
                    
                    # Handle object labels
                    if 'objectLabels' in annotation:
                        tomogram.object_labels = json.dumps(annotation['objectLabels'])
                    else:
                        tomogram.object_labels = json.dumps([])  # Empty array instead of None
                    
                    tomogram.save()
                    
                except ReviewTomogram.DoesNotExist:
                    return JsonResponse({"error": f"Tomogram not found: {annotation['tomogramId']}"}, status=404)
            
            # Update review counts
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__isnull=False
            ).count()
            
            # Just store the path in the database without creating the file
            save_path = f"/mnt/data/reviews/{review_id}/review.json"
            review.save_path = save_path
            review.status = 'completed'
            review.save()
            
            # Return success response
            return JsonResponse({
                "ok": True,
                "savedAt": datetime.utcnow().isoformat() + 'Z',
                "savePath": save_path,
                "reviewedCount": review.reviewed_count,
                "totalCount": review.total_count
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def complete_review(self, request, review_id):
        """
        Mark a review as completed.
        
        Args:
            request: HTTP request
            review_id: UUID of the review
            
        Request Body:
        {
            "reviewId": UUID
        }
        
        Returns:
        {
            "ok": true,
            "finishedAt": string (ISO timestamp),
            "savePath": string
        }
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
            
            # Validate review ID matches URL parameter
            if data.get('reviewId') != review_id:
                return JsonResponse({"error": "Review ID in request body does not match URL parameter"}, status=400)
            
            # Convert string to UUID if needed
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)
            
            # Get the review
            try:
                review = Review.objects.get(review_id=review_id)
            except Review.DoesNotExist:
                return JsonResponse({"error": "Review not found"}, status=404)
            
            # Update review status
            review.status = 'completed'
            review.save()
            
            # Return success response
            return JsonResponse({
                "ok": True,
                "finishedAt": datetime.utcnow().isoformat() + 'Z',
                "savePath": review.save_path if review.save_path else None
            })
            
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
    try:
        # Convert string to UUID if needed
        if isinstance(review_id, str):
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)
        
        # Get the review with related tomograms
        review = Review.objects.get(review_id=review_id)
        
        # Check if review is completed
        if review.status != 'completed':
            return JsonResponse({"error": "Review must be completed before exporting"}, status=400)
        
        # Get all tomograms for this review
        tomograms = ReviewTomogram.objects.filter(review=review)
        
        # Format the export data
        export_data = {
            "reviewId": str(review.review_id),
            "reviewName": review.review_name,
            "sessionId": review.session.name,
            "runId": review.run_id,
            "reconstructionType": review.reconstruction_type,
            "completedAt": review.updated_at.isoformat(),
            "annotations": []
        }
        
        # Add tomogram annotations
        for tomogram in tomograms:
            annotation = {
                "tomogramId": tomogram.tomogram_id,
                "quality": tomogram.quality if tomogram.quality else "pending",
                "rejectionReasons": [],
                "objectLabels": []
            }
            
            # Add rejection reasons if quality is rejected
            if tomogram.quality == "rejected" and tomogram.rejection_reasons:
                try:
                    annotation["rejectionReasons"] = json.loads(tomogram.rejection_reasons)
                except json.JSONDecodeError:
                    # Fallback for old format (comma-separated)
                    annotation["rejectionReasons"] = tomogram.rejection_reasons.split(",")
            
            # Add object labels if they exist
            if tomogram.object_labels:
                try:
                    annotation["objectLabels"] = json.loads(tomogram.object_labels)
                except json.JSONDecodeError:
                    # Fallback for old format (comma-separated)
                    annotation["objectLabels"] = tomogram.object_labels.split(",")
            
            export_data["annotations"].append(annotation)
        
        # Create the response with the JSON data
        response = JsonResponse(export_data)
        
        # Set headers for file download
        filename = f"review_{review_id}_export.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/json'
        
        return response
        
    except Review.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_review_tomograms(request, review_id):
    """
    Get all tomograms for a specific review.
    
    Args:
        request: HTTP request
        review_id: String ID of the review
        
    Returns:
        JSON array of tomograms with their status
        [
            { "tomogramId": "tomo_001", "status": "pending" },
            { "tomogramId": "tomo_002", "status": "rejected" }
        ]
    """
    print(f"Getting tomograms for review_id: {review_id}")
    print(f"Type of review_id: {type(review_id)}")
    
    try:
        # First check if the review exists
        try:
            # Try to convert to UUID if it's a valid UUID string
            try:
                review_uuid = uuid.UUID(review_id)
                review = Review.objects.get(review_id=review_uuid)
            except ValueError:
                # If not a valid UUID, try to find by string ID
                review = Review.objects.get(review_id=review_id)
                
            print(f"Found review: {review.review_id}")
        except Review.DoesNotExist:
            print(f"Review not found with ID: {review_id}")
            # List all available review IDs for debugging
            all_reviews = Review.objects.all()
            print("Available review IDs:")
            for r in all_reviews:
                print(f"- {r.review_id} (Name: {r.review_name})")
            return JsonResponse({"error": "Review not found"}, status=404)
        
        # Get tomograms for the review
        tomograms = ReviewTomogram.objects.filter(
            review=review
        ).values('tomogram_id', 'quality')
        
        print(f"Found {tomograms.count()} tomograms")
        
        # Format the response
        tomograms_data = [
            {
                "tomogramId": tomo['tomogram_id'],
                "status": tomo['quality'] if tomo['quality'] else 'pending'
            }
            for tomo in tomograms
        ]
        
        return JsonResponse(tomograms_data, safe=False)
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewTomogramView(View):
    def get(self, request, review_id, tomogram_id):
        """
        Get detailed information about a specific tomogram in a review.
        
        Args:
            request: HTTP request
            review_id: String ID of the review
            tomogram_id: ID of the tomogram
            
        Returns:
            JSON object with tomogram details:
            {
                "tomogramId": string,
                "displayName": string,
                "zarrPath": string,
                "existingReview": {
                    "quality": "accepted" | "rejected" | "uncertain",
                    "rejectionReasons": string[],
                    "objectLabels": string[]
                }
            }
        """
        print(f"Getting tomogram details for review_id: {review_id}, tomogram_id: {tomogram_id}")
        
        try:
            # First check if the review exists
            try:
                review = Review.objects.get(review_id=review_id)
                print(f"Found review: {review.review_id}")
            except Review.DoesNotExist:
                print(f"Review not found with ID: {review_id}")
                return JsonResponse({"error": "Review not found"}, status=404)
            
            # Get the specific tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id
                )
                print(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                print(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)
            
            # Format the response
            response_data = {
                "tomogramId": tomogram.tomogram_id,
                "displayName": f"{tomogram.position_id}",
                "zarrPath": None,
                "existingReview": None
            }
            
            # Construct zarr path based on reconstruction type
            if review.reconstruction_type.lower() == "sart":
                vol_suffix = "vol003"
                job_name = "aretomo3"
            elif review.reconstruction_type.lower() == "dctf":
                vol_suffix = "vol001"
                job_name = "aretomo3"
            else:
                vol_suffix = ""  # denoised
                job_name = "denoise"
                
            response_data["zarrPath"] = f"https://czii-onsite.czbiohub.org/krios1.processing/{job_name}/{review.session.name}/{review.run_id}/{vol_suffix}{tomogram.position_id}_Vol.zarr"
            
            # Add review details if they exist
            if tomogram.quality:
                review_data = {
                    "quality": tomogram.quality,
                    "rejectionReasons": [],
                    "objectLabels": []
                }
                
                # Add rejection reasons if quality is rejected
                if tomogram.quality == "rejected" and tomogram.rejection_reasons:
                    try:
                        review_data["rejectionReasons"] = json.loads(tomogram.rejection_reasons)
                    except json.JSONDecodeError:
                        # Fallback for old format (comma-separated)
                        review_data["rejectionReasons"] = tomogram.rejection_reasons.split(",")
                
                # Add object labels if they exist
                if tomogram.object_labels:
                    try:
                        review_data["objectLabels"] = json.loads(tomogram.object_labels)
                    except json.JSONDecodeError:
                        # Fallback for old format (comma-separated)
                        review_data["objectLabels"] = tomogram.object_labels.split(",")
                
                response_data["existingReview"] = review_data
            
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"Unexpected error in GET: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, review_id, tomogram_id):
        """
        Submit a review result for a specific tomogram.
        
        Args:
            request: HTTP request
            review_id: String ID of the review
            tomogram_id: ID of the tomogram
            
        Request Body:
        {
            "tomogramId": string,
            "quality": "accepted" | "rejected" | "uncertain",
            "rejectionReasons": string[],    // only if rejected
            "objectLabels": string[]         // optional
        }
        
        Returns:
        { "ok": true }
        """
        print(f"Submitting review result for review_id: {review_id}, tomogram_id: {tomogram_id}")
        
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
            
            # Validate required fields
            if 'quality' not in data:
                return JsonResponse({"error": "Missing required field: quality"}, status=400)
            
            # Validate quality value
            valid_qualities = ['accepted', 'rejected', 'uncertain']
            if data['quality'] not in valid_qualities:
                return JsonResponse({"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400)
            
            # Validate rejection reasons for rejected quality
            if data['quality'] == 'rejected' and not data.get('rejectionReasons'):
                return JsonResponse({"error": "Rejection reasons are required when quality is rejected"}, status=400)
            
            # Get the tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id
                )
                print(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                print(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)
            
            # Update tomogram review data
            tomogram.quality = data['quality']
            
            # Handle rejection reasons - store as JSON string
            if data['quality'] == 'rejected':
                tomogram.rejection_reasons = json.dumps(data['rejectionReasons'])
            else:
                tomogram.rejection_reasons = None
            
            # Handle object labels - store as JSON string
            if 'objectLabels' in data:
                tomogram.object_labels = json.dumps(data['objectLabels'])
            
            # Save the changes
            tomogram.save()
            
            # Update review counts
            review = tomogram.review
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__isnull=False
            ).count()
            review.save()
            
            return JsonResponse({"ok": True})
            
        except Exception as e:
            print(f"Unexpected error in POST: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

