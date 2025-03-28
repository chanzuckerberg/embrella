from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters
from django.http import JsonResponse
from django.shortcuts import render
from .agent import Aretomo3, Denoiset, StatusChecker
from umbrella.settings import ARETOMO3_SCRIPT_PATH, ARETOMO3_ADVANCED_PATH, DENOISET_SCRIPT_PATH
import os
import base64
import re
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from tem.models import MsiSession
from processes.models import JobLog
from django.db.models import F
from celery import shared_task
from django.core.cache import cache
import re
import requests
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
import time
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes

CELERY_BEAT_SCHEDULE = {
    'update_job_data_cache_every_5_seconds': {
        'task': 'workflow.tasks.update_job_data_cache',
        'schedule': 5.0,  # every 5 seconds
    },
}


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENOISET_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow',  'denoiset_template.sh')
DENOISET_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/denoise/scripts'
STATUS_CHECKER_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow',  'status_checker.sh')
STATUS_CHECKER_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/software/scripts'
KEYS = ('PixSize',
        'SplitSum',
        'Resume',
        'EerSampling',
        'McPatch',
        'Cmd',
        'McIter',
        'Group',
        'RotGain',
        'FlipGain',
        'InvGain',
        'TotalDose',
        'AlignZ',
        'VolZ',
        'ExtZ',
        'AtBin',
        'TiltAxis',
        'TiltCor',
        'AtPatch',
        'OutImod',
        'ExtPhase',
        'CorrCTF',
        'McBin',
        'Wbp')
# HOST = '10.50.120.52'
# HOST = 'login-1.czii.org'
HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')
def get_base_url():
       if ENVIRONMENT == 'staging':
           return 'http://umbrella-dev.czbiohub.org/workflow/track_jobs'
       elif ENVIRONMENT == 'production':
           return 'http://umbrella.czbiohub.org/workflow/track_jobs'
       else:  # development
           return 'http://localhost:8000/workflow/track_jobs'


def store_log(job_name, request, data_sanitized, error, advanced_status=False, job_id = None):
    JobLog.objects.create(
                user=request.user,
                job_name=job_name,
                advanced=advanced_status,
                job_id=job_id,  # No job ID available in case of error
                parameters=data_sanitized,
                error_message=str(error)  # Store the error message
            )
    
@extend_schema(
    methods=["GET"],
    description="Fetches parsed Aretomo3 JSON metadata for a given session and run ID.",
    parameters=[
        OpenApiParameter(name='session', required=True, type=OpenApiTypes.STR, description='Session name (e.g. 23sep23a)'),
        OpenApiParameter(name='run_id', required=True, type=OpenApiTypes.STR, description='Run ID (e.g. 001)'),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@login_required
def get_aretomo3_json(request):
    session_name = request.GET.get('session')
    run_id = request.GET.get('run_id')

    if not session_name or not run_id:
        error_msg = "Session name and run ID are required."
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=400)

    remote_path = f'/hpc/projects/group.czii/krios1.processing/aretomo3/{session_name}/run{run_id}/AreTomo3_Session.json'

    try:
        json_data = ssh_connect(remote_path)
        full_data = jsonify(json_data)

        # Extract version and gain
        version = full_data['software']['version']
        gain = full_data['input']['Gain']

        # Extract other parameters
        parsed_data = extract_parameters(full_data, KEYS)

        # Insert version and gain at the beginning
        ordered_parsed_data = {"Version": version, "Gain": gain, **parsed_data}

        return JsonResponse(ordered_parsed_data, safe=False)
    except FileNotFoundError as fnf_err:
        error_msg = f"File not found"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=404)
    except Exception as err:
        error_msg = f"Please check the server status: {str(err)}"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=500)
    
@extend_schema(
    methods=["POST"],
    description="Submits an advanced Aretomo3 processing job with optional gain and parameter customization.",
    request={
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "use_old_gain": {"type": "string", "enum": ["yes", "no"]},
            "user_id": {"type": "string"},
            "password": {"type": "string", "description": "Base64-encoded password"},
            "run_number": {"type": "string"},
            "denoiset_training": {"type": "string"},
            "pixel_size": {"type": "string"},
            "dose_number": {"type": "string"},
            "num_checks": {"type": "string"},
            "gain_file_name": {"type": "string"},
            "use_advanced_params": {"type": "string", "enum": ["yes", "no"]},
            "tilt_axis": {"type": "string"},
            "tilt_axis_refine": {"type": "string"},
            "align_z": {"type": "string"},
            "vol_z": {"type": "string"},
            "imod_option": {"type": "string"},
            "local_shift": {"type": "string"},
            "tilt_offset": {"type": "string"},
            "thickness_mesaure": {"type": "string"},
        },
        "required": ["project_name", "use_old_gain", "user_id", "password"]
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        422: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    }
)
@api_view(["POST"])
@csrf_exempt
def run_aretomo3_advanced(request):
    data_sanitized = {}  # Initialize this variable at the start
    if request.method == 'POST':
        data = json.loads(request.body)

        project_name = data.get('project_name')
        use_old_gain = data.get('use_old_gain')  # "yes" or "no"
        user_id = data.get('user_id')
        encoded_password = data.get('password', '')
        decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        # Validate project_name format (e.g., 23sep23a)
        project_name_pattern = re.compile(r'^\d{2}[a-z]{3}\d{2}[a-z]$')
        if not project_name_pattern.match(project_name):
            return JsonResponse(
                {'error': 'Invalid project_name format. Please check the project name: 422'},
                status=422
            )
        data_sanitized = dict(data)
        data_sanitized.pop('password', None)
        # -------------------------------------------
        # Initialize all variables to a default value
        # -------------------------------------------
        gain_file_name = None
        run_number = None
        denoiset_training = None
        pixel_size = None
        use_advanced_params = None
        tilt_axis = None
        tilt_axis_refine = None
        align_z = None
        vol_z = None
        imod_option = None
        local_shift = None
        tilt_offset = None
        thickness_mesaure = None
        dose_number = None
        num_checks = None

        try:
            # Branch: old gain
            if use_old_gain == 'yes':
                gain_file_name = data.get('gain_file_name')
                run_number = data.get('run_number')
                denoiset_training = data.get('denoiset_training')
                # evn_odd_split = data.get('evn_odd_split')
                pixel_size = data.get('pixel_size')
                use_advanced_params = data.get('use_advanced_params')
                dose_number = data.get('dose_number')
                num_checks = data.get('num_checks')
                # Only parse advanced params if user selected "yes"
                if use_advanced_params == 'yes':
                    tilt_axis = data.get('tilt_axis', "")
                    tilt_axis_refine = data.get('tilt_axis_refine')
                    align_z = data.get('align_z', "")
                    vol_z = data.get('vol_z', "")
                    imod_option = data.get('imod_option')
                    local_shift = data.get('local_shift')
                    tilt_offset = data.get('tilt_offset')
                    thickness_mesaure = data.get('thickness_mesaure')

            # Branch: no old gain
            elif use_old_gain == 'no':
                run_number = data.get('run_number')
                denoiset_training = data.get('denoiset_training')
                # evn_odd_split = data.get('evn_odd_split')
                pixel_size = data.get('pixel_size')
                use_advanced_params = data.get('use_advanced_params')

                dose_number = data.get('dose_number')
                num_checks = data.get('num_checks')

                if use_advanced_params == 'yes':
                    tilt_axis = data.get('tilt_axis', "")
                    tilt_axis_refine = data.get('tilt_axis_refine')
                    align_z = data.get('align_z', "")
                    vol_z = data.get('vol_z', 1200)
                    imod_option = data.get('imod_option')
                    local_shift = data.get('local_shift')
                    tilt_offset = data.get('tilt_offset')
                    thickness_mesaure = data.get('thickness_mesaure')
            
            else:
                return JsonResponse(
                    {'error': 'Invalid use_old_gain value. Must be "yes" or "no": 422'},
                    status=422
                )

            # Store user credentials in session
            request.session['user_id'] = user_id
            request.session['decoded_password'] = decoded_password

            # Initialize the Aretomo3 object and connect
            aretomo = Aretomo3(
                HOST, PORT, user_id, decoded_password, ARETOMO3_ADVANCED_PATH
            )
            aretomo.connect()

            # Now you can safely call the script, because the variables
            # you pass in are guaranteed to have *some* default value.
            # Option 1: Provide a format string with placeholders
            logger.info(
                "Project: %s, Use Old Gain: %s, Advanced Params: %s, Pixel Size: %s, Denoise Training: %s",
                project_name,
                use_old_gain,
                use_advanced_params,
                pixel_size,
                denoiset_training
            )

            output, error = aretomo.run_advanced_script(
                project_name=project_name,
                use_old_gain=use_old_gain,
                run_number=run_number,
                pixel_size=pixel_size,
                dose_number=dose_number,
                num_checks=num_checks,
                gain_file_name=gain_file_name,
                denoise_training=denoiset_training,
                # even_odd_split=evn_odd_split,
                use_advanced_params=use_advanced_params,
                tilt_axis=tilt_axis,
                tilt_axis_refine=tilt_axis_refine,
                align_z=align_z,
                vol_z=vol_z,
                imod_option=imod_option,
                local_shift=local_shift,
                tilt_offset=tilt_offset,
                thickness_mesaure=thickness_mesaure,
                user_id=user_id
            )

            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            print(found_ids)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Store log regardless of success or failure
            store_log(job_name='Aretomo3',request=request, data_sanitized=data_sanitized, error=None, advanced_status=True, job_id=job_id_str)

            # Return your response
            return JsonResponse({
                'message': f'Advanced job for project {project_name} submitted successfully.',
                'output': output,
                'error': error
            })

        except Exception as e:
            logger.error(f'Error in run_aretomo3_advanced: {str(e)}')
            store_log(job_name='Aretomo3',request=request, data_sanitized=data_sanitized, error=str(e), advanced_status=True, job_id=None)
            return JsonResponse({'error': str(e)}, status=500)

        finally:
            # Ensure we always close the connection if we opened it
            if 'aretomo' in locals():
                aretomo.close()

    # Handle invalid request method
    return JsonResponse({'error': 'Invalid request method: 400'}, status=400)



@extend_schema(
    methods=["POST"],
    description="Submits a standard Aretomo3 job for the specified session.",
    request={
        "type": "object",
        "properties": {
            "session_name": {"type": "string", "description": "Session identifier (e.g. 23sep23a)"},
            "run_number": {"type": "string"},
            "pixel_size": {"type": "string"},
            "total_dose": {"type": "string"},
            "num_checks": {"type": "string"},
            "user_id": {"type": "string"},
            "password": {"type": "string", "description": "Base64-encoded SSH password"},
        },
        "required": ["session_name", "run_number", "pixel_size", "total_dose", "num_checks", "user_id", "password"]
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        422: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
@login_required
def run_aretomo3(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_name = data.get('session_name')
        run_number = data.get('run_number')
        pix_size = data.get('pixel_size')
        total_dose = data.get('total_dose')
        num_checks = data.get('num_checks')
        user_id = data.get('user_id')
        encoded_password = data.get('password')
        decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        # Validate session_name format
        session_name_pattern = re.compile(r'^\d{2}[a-z]{3}\d{2}[a-z]$')
        if not session_name_pattern.match(session_name):
            return JsonResponse({'error': 'Invalid session_name format. Please check the session name: 422'}, status=422)

        # Store user_id and decoded_password in session
        request.session['user_id'] = user_id
        request.session['decoded_password'] = decoded_password

        data_sanitized = dict(data)
        data_sanitized.pop('password', None)
        job_id_str = None  # Initialize job_id_str to avoid referencing it before assignment

        try:
            aretomo = Aretomo3(HOST, PORT, user_id, decoded_password, ARETOMO3_SCRIPT_PATH)
            # Connect to the remote server
            aretomo.connect()

            # Run the script and get the output
            output, error = aretomo.run_script(session_name, run_number, pix_size, total_dose, num_checks, user_id)

            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Log success without an error message
            store_log(job_name='Aretomo3',
                      request=request,
                      data_sanitized=data_sanitized,
                      error="",
                      advanced_status=False,
                      job_id=job_id_str)

            return JsonResponse({
                'message': f'Session {session_name} for Aretomo3 is submitted successfully. Please check the output directory below',
                'output': output,
                'error': error
            })
        except Exception as e:
            # Log the error details
            store_log(job_name='Aretomo3',
                      request=request,
                      data_sanitized=data_sanitized,
                      error=str(e),
                      advanced_status=False,
                      job_id=job_id_str)
            return JsonResponse({'error': str(e) + ': 500'}, status=500)
        finally:
            aretomo.close()
    else:
        # For non-POST requests, log the error and return a 400 status
        default_data = {}
        store_log(job_name='Aretomo3',
                  request=request,
                  data_sanitized=default_data,
                  error="Invalid request method",
                  advanced_status=False,
                  job_id=None)
        return JsonResponse({'error': 'Invalid request method: 400'}, status=400)



@extend_schema(
    methods=["GET"],
    description="Returns the currently authenticated user's username (email prefix).",
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@csrf_exempt
@login_required
def user_info(request):
    username = request.user.username.split('@')[0]
    response_data = {"username": username}
    return JsonResponse(response_data, safe=False, status=200)

@extend_schema(
    methods=["POST"],
    description="Cancels a submitted SLURM job on the remote server.",
    request={
        "type": "object",
        "properties": {
            "job_number": {"type": "string", "description": "The job ID to cancel"},
            "user_id": {"type": "string", "description": "Remote login user ID"},
            "password": {"type": "string", "description": "Base64-encoded remote password"},
        },
        "required": ["job_number"]
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@login_required
def cancel_jobs(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        job_number = data.get('job_number')
        
        
        # Retrieve user_id and decoded_password from session
        user_id = request.session.get('user_id')
        decoded_password = request.session.get('decoded_password')

        if user_id is None and decoded_password is None:
            user_id = data.get('user_id')
            encoded_password = data.get('password')
            decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        # if not user_id or not decoded_password:
        #     return JsonResponse({'error': 'User credentials not found in session'}, status=400)

        aretomo = Aretomo3(HOST, PORT, user_id, decoded_password, ARETOMO3_SCRIPT_PATH)

        try:
            # Connect to the remote server
            aretomo.connect()

            output, error = aretomo.cancel(job_number)
            return JsonResponse(
                {'message': f'Job - {job_number} for Aretomo3 is canceld successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            aretomo.close()

    return JsonResponse({'error': 'Invalid request method'}, status=400)
@csrf_exempt
def track_jobs(request):
    """
    Handle a GET request to track jobs. If 'job_name' is specified in 
    the query parameters, track only that job. Otherwise, track all jobs.
    """
    if request.method == 'GET':
        job_name = request.GET.get('job_name')  # None if not provided

        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH)
        try:
            # Connect to the remote server
            aretomo.connect()

            if job_name is None:
                output, error = aretomo.track_jobs(job_name=None, all=True)
            else:
                output, error = aretomo.track_jobs(job_name)

            formatted_output = format_job_output(output)
            return JsonResponse({'jobs': formatted_output})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            aretomo.close()

    # If the request is not GET, return an error
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def format_job_output(output):
    # Split the output into lines
    lines = output.strip().split('\n')
    # Extract the header and job details
    header = lines[0].split()
    job_details = lines[1:]

    jobs = []
    for job in job_details:
        # Split job data into parts based on whitespace
        job_data = job.split()

        # Initialize a dictionary for the job info
        job_info = {}

        # Assign values to the corresponding headers
        job_info['JOBID'] = job_data[0]
        job_info['PARTITION'] = job_data[1]
        job_info['NAME'] = job_data[2]
        job_info['USER'] = job_data[3]
        job_info['ST'] = job_data[4]
        job_info['TIME'] = job_data[5]
        job_info['NODES'] = job_data[6]

        # The remaining part is NODELIST(REASON)
        job_info['NODELIST(REASON)'] = ' '.join(job_data[7:])

        jobs.append(job_info)

    return jobs
def custom_workflow_page(request):
    return render(request, 'workflows/workflow_page.html')

def custom_run_workflow_page(request):
    return render(request, 'workflows/workflow_run.html')

def cutom_run_denoise_workflow_page(request):
    return render(request, 'workflows/workflow_denoise_run.html')

def custom_workflow_cancel(request):
    return render(request, 'workflows/workflow_cancel.html')

def custom_workflow_track(request):
    return render(request, 'workflows/workflow_track.html')

def custom_workflow_logs(request):
    return render(request, 'workflows/workflow_logs.html')

@extend_schema(
    methods=["GET"],
    description="Returns a list of all MSI session names.",
    responses={
        200: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_msi_session_list(request):
    try:
        # Fetch only the name field from MsiSession
        session_names = list(MsiSession.objects.values_list('name', flat=True))
        
        return JsonResponse({'session_names': session_names}, status=200)

    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns MSI sessions and associated run numbers. Filters by session name if provided.",
    parameters=[
        OpenApiParameter(name='session_name', required=False, type=OpenApiTypes.STR, description='Optional MSI session name to filter')
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_msi_params_list(request):
    try:
        # Get the msi_session name from request parameters
        session_name_filter = request.GET.get('session_name', None)

        # Perform the join between tem_msisession and processes_procrun
        query = (
            MsiSession.objects
            .annotate(
                run_number=F('procrun__name'),  # Map the 'name' field from the procrun table
                run_created_at=F('procrun__created_at')  # Include the created_at field for sorting
            )
            .values('name', 'run_number', 'run_created_at')
        )

        # Apply filtering if a session name is provided
        if session_name_filter:
            query = query.filter(name=session_name_filter)

        # Group results by name and collect unique run numbers with sorting by created_at
        grouped_sessions = {}
        for entry in query:
            name = entry['name']
            run_number = entry['run_number']
            created_at = entry['run_created_at']
            if name not in grouped_sessions:
                grouped_sessions[name] = []
            if run_number:
                # Remove 'run' prefix if it exists
                stripped_run_number = run_number.replace("run", "")
                grouped_sessions[name].append((stripped_run_number, created_at))

        # Sort run numbers by created_at (most recent first) and format the response
        formatted_sessions = [
            {
                "name": name,
                "run_numbers": [run[0] for run in sorted(run_numbers, key=lambda x: x[1], reverse=True)]
            }
            for name, run_numbers in grouped_sessions.items()
        ]

        return JsonResponse({'sessions': formatted_sessions}, status=200)

    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

@extend_schema(
    methods=["GET"],
    description="Returns job logs for all users or filters by a specific username if provided.",
    parameters=[
        OpenApiParameter(name='user_name', required=False, type=OpenApiTypes.STR, description='Filter logs by user name')
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_job_logs(request):
    try:
        # Extract user_name from query parameters
        user_name = request.GET.get('user_name', None)

        # Fetch all JobLog entries
        job_logs = JobLog.objects.all().values(
            'user', 
            'job_name', 
            'advanced', 
            'job_id', 
            'created_at', 
            'parameters', 
            'error_message'
        )

        job_logs_list = list(job_logs)

        # Flip 'user' -> 'user_id' and 'parameters.user_id' -> 'parameters.user'
        filtered_job_logs = []
        for entry in job_logs_list:
            # 1) Rename top-level 'user' to 'user_id'
            entry['user_id'] = entry.pop('user', None)
            
            # 2) Inside 'parameters', rename 'user_id' to 'user'
            params = entry.get('parameters', {})
            if 'user_id' in params:
                params['user'] = params.pop('user_id')
            
            # Update the entry's parameters
            entry['parameters'] = params

            # 3) Filter by user_name if provided
            if user_name is None or (params.get('user') == user_name):
                filtered_job_logs.append(entry)

        return JsonResponse({'job_logs': filtered_job_logs}, status=200)

    except Exception as e:
        logger.error(f'An unexpected error occurred while fetching job logs: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    
@extend_schema(
    methods=["POST"],
    description="Submits a DenoisET job for a given MSI session and run number.",
    request={
        "type": "object",
        "properties": {
            "session_name": {"type": "string"},
            "run_number": {"type": "string"},
            "model_name": {"type": "string"},
            "denoise_run_number": {"type": "string"},
            "user_id": {"type": "string"},
            "password": {"type": "string", "description": "Base64-encoded password"},
            "live_denoising": {"type": "boolean", "default": False}
        },
        "required": ["session_name", "run_number", "model_name", "denoise_run_number", "user_id", "password"]
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["POST"])
# @login_required
@csrf_exempt
def run_denoiset(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_name = data.get('session_name')
            run_number = data.get('run_number')
            model_name = data.get('model_name')
            denoise_run_number = data.get('denoise_run_number')
            user_id = data.get('user_id')
            encoded_password = data.get('password')
            decoded_password = base64.b64decode(encoded_password).decode('utf-8')

            # Store user_id and decoded_password in session
            request.session['user_id'] = user_id
            request.session['decoded_password'] = decoded_password

            data_sanitized = dict(data)
            print(data_sanitized)
            data_sanitized.pop('password', None)

            # Create the Denoiset instance.
            denoiset = Denoiset(
                HOST, 
                PORT, 
                user_id, 
                decoded_password, 
                DENOISET_SCRIPT_PATH, 
                DENOISET_TEMPLATE_PATH
            )

            # Connect to the remote server.
            denoiset.connect()

            # Retrieve the live denoising flag; defaults to False if not provided.
            live_denoising = data.get('live_denoising', False)

            # Run the denoising script and get the output.
            output, error = denoiset.run_script(session_name, run_number, denoise_run_number, model_name, user_id, live_denoising)

            # Extract the job ID(s) from the output.
            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Log the successful submission.
            store_log(
                job_name='DenoisET',
                request=request, 
                data_sanitized=data_sanitized, 
                error="", 
                advanced_status=True, 
                job_id=job_id_str
            )

            return JsonResponse({
                'message': f'Session {session_name} for Denoiset is submitted successfully. Please check the output directory.',
                'output': output,
                'error': error
            })

        except Exception as e:
            # Log error details.
            store_log(
                job_name='DenoisET',
                request=request, 
                data_sanitized=data_sanitized if 'data_sanitized' in locals() else {}, 
                error=str(e), 
                advanced_status=False, 
                job_id=None
            )
            return JsonResponse({'error': str(e) + ': 500'}, status=500)

        finally:
            # Ensure the SSH connection is closed.
            if 'denoiset' in locals():
                denoiset.close()

    # For non-POST requests.
    store_log(
        job_name='DenoisET',
        request=request, 
        data_sanitized={}, 
        error="Invalid request method", 
        advanced_status=False, 
        job_id=None
    )
    return JsonResponse({'error': 'Invalid request method: 400'}, status=400)

# views.py
def dashboard(request):
    """
    Render the dashboard page with the dynamic graph.
    """
    return render(request, 'workflows/workflow_dashboard.html')


        
@csrf_exempt
def workflow_get_data(request):
    """
    Fetch all job data directly from the internal track_jobs functionality.
    Process it by counting jobs either per job name or per user based on 
    the 'group_by' request parameter.
    """
    try:
        # Initialize and connect to Aretomo
        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH)
        aretomo.connect()

        # Since we want all jobs, set job_name=None and all=True
        output, error = aretomo.track_jobs(job_name=None, all=True)

        # Close the connection in the finally block
        formatted_output = format_job_output(output)
        # `formatted_output` should be a list of job dicts, e.g.:
        # [{'USER': '...', 'NAME': '...'}, ...]

        # Check for a 'group_by' GET parameter, defaulting to 'job' if not provided.
        group_by = request.GET.get('group_by', 'job').lower()
        logger.debug(f"group_by parameter: {group_by}")

        # Now we reuse the grouping logic
        if group_by == 'user':
            # Group jobs by user -> user_counts[user][job_name] = count
            user_counts = {}
            for job in formatted_output:
                user = job.get('USER', 'Unknown')
                job_name = job.get('NAME', 'Unknown')
                user_counts.setdefault(user, {})
                user_counts[user][job_name] = user_counts[user].get(job_name, 0) + 1
            result = user_counts
        else:
            # Default: group jobs by job name -> name_counts[job_name] = count
            name_counts = {}
            for job in formatted_output:
                job_name = job.get('NAME', 'Unknown')
                name_counts[job_name] = name_counts.get(job_name, 0) + 1
            result = name_counts

    except Exception as e:
        logger.exception("An error occurred while fetching or processing data.")
        result = {"error": str(e)}
    finally:
        # Ensure the connection is closed even if an exception is raised
        try:
            aretomo.close()
        except:
            pass

    return JsonResponse(result)

def parse_script_output(raw_output):
    """
    Parse the raw output string from the status-check script into a structured dict.
    
    Expected raw_output example:
        1) Number of raw data .mdoc files: 323
        2) Alignment files in aretomo3:
           run001: 298
        3) SART volumes in aretomo3:
           run001: 296
        4) Denoise volumes in denoise:
    
    Returns a dict similar to:
        {
            "raw_data_files": 323,
            "alignment_files": {"run001": 298},
            "sart_volumes": {"run001": 296},
            "denoise_volumes": {}
        }
    """
    result = {}
    current_section = None
    for line in raw_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("1)"):
            # e.g., "1) Number of raw data .mdoc files: 323"
            try:
                number = int(stripped.split(":")[-1].strip())
                result["raw_data_files"] = number
            except Exception:
                result["raw_data_files"] = None
        elif stripped.startswith("2)"):
            current_section = "alignment_files"
            result[current_section] = {}
        elif stripped.startswith("3)"):
            current_section = "sart_volumes_aretomo"
            result[current_section] = {}
        elif stripped.startswith("4)"):
            current_section = "denoise_volumes"
            result[current_section] = {}
        else:
            # Lines in the indented sections like "run001: 298"
            if current_section and ":" in stripped:
                try:
                    key, val = stripped.split(":", 1)
                    result[current_section][key.strip()] = int(val.strip())
                except Exception:
                    result[current_section][key.strip()] = val.strip()
    return result


@extend_schema(
    methods=["GET"],
    description="Triggers a remote status check for a given session via SSH.",
    parameters=[
        OpenApiParameter(
            name='session_name',
            required=True,
            type=OpenApiTypes.STR,
            description="MSI session name used to run the status-check script"
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(["GET"])
@require_http_methods(["GET"])
@csrf_exempt
def status_check_api(request):
    """
    API endpoint to trigger a remote status check via a GET call.
    Expects a query parameter: ?session_name=your_session_id

    The SSH credentials and configuration are read from environment variables/constants:
      - HOST, PORT, USERNAME, PASSWORD
      - STATUS_CHECKER_SCRIPT_PATH (remote_script_dir)
      - STATUS_CHECKER_TEMPLATE_PATH (local_template_path)
    """
    session_name = request.GET.get('session_name')
    if not session_name:
        return JsonResponse({"error": "Missing 'session_name' parameter."}, status=400)

    try:
        # Load credentials and configuration from environment variables/constants
        remote_script_dir = STATUS_CHECKER_SCRIPT_PATH
        local_template_path = STATUS_CHECKER_TEMPLATE_PATH


        if not all([HOST, PORT, USERNAME, PASSWORD, remote_script_dir, local_template_path]):
            return JsonResponse(
                {"error": "Server configuration incomplete. Please check environment variables."},
                status=500
            )

        # Instantiate and use the StatusChecker
        status_checker = StatusChecker(
            HOST, PORT, USERNAME, PASSWORD, remote_script_dir, local_template_path
        )
        status_checker.connect()
        # live_denoising is set to False by default
        raw_output, script_error = status_checker.check_status(session_name, live_denoising=False)
        status_checker.close()

        # Parse the raw output into a structured dictionary
        parsed_output = parse_script_output(raw_output)

        response_data = {"result": parsed_output}
        if script_error.strip():
            response_data["error"] = script_error.strip()

        return JsonResponse(response_data, status=200, json_dumps_params={'indent': 4})

    except Exception as e:
        logger.exception("Error during status check API")
        return JsonResponse({"error": str(e)}, status=500)