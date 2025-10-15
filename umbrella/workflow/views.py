from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters, hostname, port, username, password, ssh_file_exists, ssh_list_directory
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.decorators import api_view, permission_classes
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
from processes.models import ProcPlan
from django.views.decorators.http import require_http_methods
from tem.models import MsiSession
from processes.models import JobLog
from django.db.models import F
from celery import shared_task
from django.core.cache import cache
import re
import requests
from django.http import StreamingHttpResponse
from django.core.cache import cache
from workflow.utils import ssh_connect
import time
import pandas as pd
import paramiko
from io import StringIO
import subprocess
import logging
from processes.models import ProcRun
CELERY_BEAT_SCHEDULE = {
    'update_job_data_cache_every_5_seconds': {
        'task': 'workflow.tasks.update_job_data_cache',
        'schedule': 5.0,  # every 5 seconds
    },
}


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENOISET_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow', 'denoiset_template.sh')
DENOISET_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/denoise/scripts'
STATUS_CHECKER_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow', 'status_checker.sh')
STATUS_CHECKER_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/software/scripts'
ARETOMO3_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow', 'templates', 'workflows', 'aretomo3_advanced_template.sh')
ARETOMO3_BASIC_TEMPLATE_PATH = os.path.join(BASE_DIR, 'workflow', 'templates', 'workflows', 'aretomo3_basic_template.sh')
ARETOMO3_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/scripts'
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
METADATA_SUMMARY_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/'
DATA_COLLECTION_PATH = '/hpc/instruments/czii.krios1/OffloadData/'
HOSTNAME = 'https://czii-onsite.czbiohub.org/krios1.processing/aretomo3/'
ARETOMO3_PROCESSING_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/'

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
@permission_classes([IsAuthenticated])
@login_required
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
        frame_dose = None  # Changed from num_checks to frame_dose

        try:
            # Branch: old gain
            if use_old_gain == 'yes':
                gain_file_name = data.get('gain_file_name')
                run_number = data.get('run_number')
                denoiset_training = data.get('denoiset_training')
                pixel_size = data.get('pixel_size')
                use_advanced_params = data.get('use_advanced_params')
                dose_number = data.get('dose_number')
                frame_dose = data.get('frame_dose')  # Changed from num_checks to frame_dose
                # Only parse advanced params if user selected "yes"
                if use_advanced_params == 'yes':
                    tilt_axis = data.get('tilt_axis', "")
                    tilt_axis_refine = data.get('tilt_axis_refine')
                    align_z = data.get('align_z', "")
                    vol_z = data.get('vol_z', "")
                    imod_option = data.get('imod_option')
                    local_shift = data.get('local_shift')
                    tilt_offset = data.get('tilt_offset')
                    thickness_mesaure = data.get('thickness_measure')

            # Branch: no old gain
            elif use_old_gain == 'no':
                run_number = data.get('run_number')
                denoiset_training = data.get('denoiset_training')
                pixel_size = data.get('pixel_size')
                use_advanced_params = data.get('use_advanced_params')
                dose_number = data.get('dose_number')
                frame_dose = data.get('frame_dose')  # Changed from num_checks to frame_dose

                if use_advanced_params == 'yes':
                    tilt_axis = data.get('tilt_axis', "")
                    tilt_axis_refine = data.get('tilt_axis_refine')
                    align_z = data.get('align_z', "")
                    vol_z = data.get('vol_z', 1200)
                    imod_option = data.get('imod_option')
                    local_shift = data.get('local_shift')
                    tilt_offset = data.get('tilt_offset')
                    thickness_mesaure = data.get('thickness_measure')
            
            else:
                return JsonResponse(
                    {'error': 'Invalid use_old_gain value. Must be "yes" or "no": 422'},
                    status=422
                )

            # Check if run number already exists in the database
            try:
                # Get the session and plan (project_name is the same as session_name in this context)
                msi_session = MsiSession.objects.get(name=project_name)
                proc_plan = ProcPlan.objects.get(name='czii-live')  # AreTomo3 uses czii-live plan
                
                # Ensure the run number has the correct format (e.g., "run001")
                if not run_number.startswith('run'):
                    run_number = f"run{run_number.zfill(3)}"
                
                # Check if this run number already exists for this session and plan
                existing_run = ProcRun.objects.filter(
                    name=run_number,
                    msi_session=msi_session,
                    proc_plan=proc_plan
                ).first()
                
                if existing_run:
                    return JsonResponse({
                        'error': f'Run number {run_number} already exists for session {project_name}. Please choose a different run number.'
                    }, status=400)
                    
            except MsiSession.DoesNotExist:
                return JsonResponse({'error': f'Session {project_name} not found in database'}, status=404)
            except ProcPlan.DoesNotExist:
                return JsonResponse({'error': 'AreTomo3 processing plan (czii-live) not found'}, status=404)

            # Store user credentials in session
            request.session['user_id'] = user_id
            request.session['decoded_password'] = decoded_password

            # Initialize the Aretomo3 object and connect
            aretomo = Aretomo3(
                HOST, 
                PORT, 
                user_id, 
                decoded_password,
                ARETOMO3_SCRIPT_PATH,  # remote_script_dir
                ARETOMO3_TEMPLATE_PATH  # local_template_path
            )
            aretomo.connect()

            # Now you can safely call the script, because the variables
            # you pass in are guaranteed to have *some* default value.
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
                frame_dose=frame_dose,  # Changed from num_checks to frame_dose
                gain_file_name=gain_file_name,
                denoise_training=denoiset_training,
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
                'error': error,
                'job_id': job_id_str
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
@login_required
@csrf_exempt
def run_aretomo3(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_name = data.get('session_name')
        run_number = data.get('run_number')
        pix_size = data.get('pixel_size')
        total_dose = data.get('dose_number')
        frame_dose = data.get('frame_dose')  # Changed from num_checks to frame_dose
        user_id = data.get('user_id')
        encoded_password = data.get('password')
        decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        # Validate session_name format
        session_name_pattern = re.compile(r'^\d{2}[a-z]{3}\d{2}[a-z]$')
        if not session_name_pattern.match(session_name):
            return JsonResponse({'error': 'Invalid session_name format. Please check the session name: 422'}, status=422)

        # Check if run number already exists in the database
        try:
            # Get the session and plan
            msi_session = MsiSession.objects.get(name=session_name)
            proc_plan = ProcPlan.objects.get(name='czii-live')  # AreTomo3 uses czii-live plan
            
            # Ensure the run number has the correct format (e.g., "run001")
            if not run_number.startswith('run'):
                run_number = f"run{run_number.zfill(3)}"
            
            # Check if this run number already exists for this session and plan
            existing_run = ProcRun.objects.filter(
                name=run_number,
                msi_session=msi_session,
                proc_plan=proc_plan
            ).first()
            
            if existing_run:
                return JsonResponse({
                    'error': f'Run number {run_number} already exists for session {session_name}. Please choose a different run number.'
                }, status=400)
                
        except MsiSession.DoesNotExist:
            return JsonResponse({'error': f'Session {session_name} not found in database'}, status=404)
        except ProcPlan.DoesNotExist:
            return JsonResponse({'error': 'AreTomo3 processing plan (czii-live) not found'}, status=404)

        # Store user_id and decoded_password in session
        request.session['user_id'] = user_id
        request.session['decoded_password'] = decoded_password

        data_sanitized = dict(data)
        data_sanitized.pop('password', None)
        job_id_str = None

        try:
            aretomo = Aretomo3(
                HOST, 
                PORT, 
                user_id, 
                decoded_password,
                ARETOMO3_SCRIPT_PATH,  # remote_script_dir
                ARETOMO3_BASIC_TEMPLATE_PATH  # local_template_path
            )
            # Connect to the remote server
            aretomo.connect()

            # Run the script and get the output
            output, error = aretomo.run_script(session_name, run_number, pix_size, total_dose, frame_dose, user_id)

            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Log success without an error message
            store_log(job_name='Aretomo3',
                      request=request,
                      data_sanitized=data_sanitized,
                      error="",
                      advanced_status=False,
                      job_id=job_id_str)

            # Trigger the AreTomo3 syncer script
            try:
                syncer_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'processes', 'scripts', 'aretomo3_syncer.py')
                # Run the syncer once with job tracking
                subprocess.Popen(['python', syncer_script_path, 
                                '--session', session_name,
                                '--run', run_number,
                                '--job-id', job_id_str], 
                               env=dict(os.environ, 
                                      PYTHONPATH=os.path.dirname(os.path.dirname(__file__))))
                logging.info(f"Started AreTomo3 syncer for session {session_name}, run {run_number}, tracking job {job_id_str}")
            except Exception as e:
                logging.error(f"Failed to start AreTomo3 syncer: {str(e)}")

            return JsonResponse({
                'message': f'Session {session_name} for Aretomo3 is submitted successfully. Please check the output directory below',
                'output': output,
                'error': error,
                'job_id': job_id_str
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

        aretomo = Aretomo3(HOST, PORT, user_id, decoded_password, ARETOMO3_SCRIPT_PATH, ARETOMO3_TEMPLATE_PATH)

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

        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH, ARETOMO3_TEMPLATE_PATH)
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
        # Fetch session names and sort them
        session_names = list(MsiSession.objects.values_list('name', flat=True))
        
        # Sort the session names
        def sort_key(name):
            try:
                # Extract components from the name
                year = int(name[:2])
                month = name[2:5].lower()  # Convert to lowercase for consistent comparison
                day = int(name[5:7])
                seq = name[7] if len(name) > 7 else 'a'  # Default to 'a' if no sequence letter
                
                # Convert month to number for proper sorting
                month_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                
                # Check if month is valid
                if month not in month_map:
                    return (0, 0, 0, 'z')  # Move invalid months to the end
                
                month_num = month_map[month]
                
                # Validate year and day
                if not (0 <= year <= 99) or not (1 <= day <= 31):
                    return (0, 0, 0, 'z')  # Move invalid dates to the end
                
                # Return tuple for sorting (negative year for descending order)
                return (-year, -month_num, -day, seq)
            except (ValueError, IndexError):
                # If name doesn't match expected format, put it at the end
                return (0, 0, 0, 'z')
        
        # Sort the session names using our custom sort key
        sorted_session_names = sorted(session_names, key=sort_key)
        
        return JsonResponse({'session_names': sorted_session_names}, status=200)

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
        plan_type = request.GET.get('plan_type', 'aretomo3')  # Default to aretomo3 for backward compatibility

        # Get the plan ID based on plan type
        if plan_type == 'denoise':
            plan_name = 'czii-denoise'
        elif plan_type == 'aretomo3':
            plan_name = 'czii-live'

        logger.info(f"Plan type: {plan_type}, Plan name: {plan_name}")

        # Get the plan ID
        try:
            plan = ProcPlan.objects.get(name=plan_name)
            plan_id = plan.id
            logger.info(f"Found plan {plan_name} with ID: {plan_id}")
        except ProcPlan.DoesNotExist:
            logger.error(f"Processing plan {plan_name} not found")
            return JsonResponse({'error': f'Processing plan {plan_name} not found'}, status=404)

        # Perform the join between tem_msisession and processes_procrun
        # Let's try a more explicit query to debug the issue
        query = (
            MsiSession.objects
            .filter(procrun__proc_plan_id=plan_id)  # Filter by processing plan first
            .annotate(
                run_number=F('procrun__name'),  # Map the 'name' field from the procrun table
                run_created_at=F('procrun__created_at')  # Include the created_at field for sorting
            )
            .values('name', 'run_number', 'run_created_at')
            .distinct()  # Remove duplicates
        )

        # Apply filtering if a session name is provided
        if session_name_filter:
            query = query.filter(name=session_name_filter)

        # Let's also check what's in the ProcRun table directly for debugging
        from processes.models import ProcRun
        direct_procrun_query = ProcRun.objects.filter(proc_plan_id=plan_id)
        if session_name_filter:
            direct_procrun_query = direct_procrun_query.filter(msi_session__name=session_name_filter)
        
        direct_results = list(direct_procrun_query.values('msi_session__name', 'name', 'created_at'))
        logger.info(f"Direct ProcRun query returned {len(direct_results)} results for plan_id={plan_id}")
        for entry in direct_results:
            logger.info(f"Direct ProcRun result: {entry}")

        # Execute the query and log the results for debugging
        query_results = list(query)
        logger.info(f"Query returned {len(query_results)} results for plan_id={plan_id}, session_name_filter={session_name_filter}")
        for entry in query_results:
            logger.info(f"Query result: {entry}")

        # Group results by name and collect unique run numbers with sorting by created_at
        grouped_sessions = {}
        for entry in query_results:
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
                'error': error,
                'job_id': job_id_str
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
        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH, ARETOMO3_TEMPLATE_PATH)
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
    
"""
Metadata Summary
"""

# Helper function for natural sorting
def natural_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def preprocess_csv(metrics_path, timestamp_path, thumbnail_base_url, ctf_base_url, merge="continue"):
    try:
        # Load data from remote server using ssh_connect
        logger.info(f"Attempting to read metrics file: {metrics_path}")
        metrics_content = ssh_connect(metrics_path)
        logger.info(f"Successfully read metrics file")
        
        # Convert string content to pandas DataFrame
        metrics_df = pd.read_csv(StringIO(metrics_content))
        
        # Normalize
        metrics_df["Tilt_Series"] = metrics_df["Tilt_Series"].str.replace(".mrc", "", regex=False)
        
        # Sort Tilt_Series using natural sort
        metrics_df = metrics_df.sort_values(by="Tilt_Series", key=lambda col: col.map(natural_key)).reset_index(drop=True)
        
        if merge == "True":
            logger.info(f"Attempting to read timestamp file: {timestamp_path}")
            timestamp_content = ssh_connect(timestamp_path)
            logger.info(f"Successfully read timestamp file")
            
            # Convert string content to pandas DataFrame
            timestamp_df = pd.read_csv(StringIO(timestamp_content))
            
            # Merge metrics with timestamp
            merged_df = pd.merge(metrics_df, timestamp_df, on="Tilt_Series", how="left")

            # Add thumbnail paths directly to the merged dataframe
            merged_df["thumbnail_path"] = merged_df["Tilt_Series"].apply(
                lambda ts: f"{thumbnail_base_url}{ts}.jpeg"
            )
            merged_df["ctf_path"] = merged_df["Tilt_Series"].apply(
                lambda ts: f"{ctf_base_url}{ts}.jpeg"
            )
            
            # Sort Tilt_Series using natural sort
            merged_df = merged_df.sort_values(by="Tilt_Series", key=lambda col: col.map(natural_key)).reset_index(drop=True)
            
            return merged_df
        else:
            return metrics_df
            
    except Exception as e:
        logger.error(f"Error in preprocess_csv: {str(e)}")
        raise


def compute_stats(df: pd.DataFrame) -> list:
    # Get pixel size for conversion to Ångströms
    pixel_size = df['Pix_Size(A)'].iloc[0]

    # Create columns with Ångström values
    df['Thickness(A)'] = df['Thickness(Pix)'] * pixel_size
    df['Global_Shift(A)'] = df['Global_Shift(Pix)'] * pixel_size
    # Handle Defocus(A) column - if it doesn't exist, we'll skip it in statistics
    # If it exists, process it normally
    if 'Defocus(A)' in df.columns:
        try:
            df['Defocus(A)'] = df['Defocus(A)']
        except Exception as e:
            logger.error(f"Error preprocessing Defocus(A) in compute_stats: {str(e)}")
            df['Defocus(A)'] = 0
    else:
        df['Defocus(A)'] = 0


    if 'ExtPhase(Deg)' in df.columns:
        try:
            df['ExtPhase(Deg)'] = df['ExtPhase(Deg)']
        except Exception as e:
            logger.error(f"Error preprocessing ExtPhase in compute_stats: {str(e)}")
            df['ExtPhase(Deg)'] = 0
    else:
        df['ExtPhase(Deg)'] = 0

    column_mapping = {
        'CTF_Score': 'CTF Score',
        'Defocus(A)': 'Defocus (Å)',
        'ExtPhase(Deg)': 'ExtPhase',
        'CTF_Res(A)': 'CTF Resolution (Å)',
        'Thickness(A)': 'Thickness (Å)',
        'Tilt_Axis': 'Tilt Axis (°)',
        'Global_Shift(A)': 'Global Shift (Å)',   
        'Bad_Patch_Low': 'Bad patch low_angle (fraction)',
        'Bad_Patch_All': 'Bad patch all_angle (fraction)',
        'Alpha0': 'Alpha Offset (°)',
        'Beta0': 'Beta Offset (°)'
    }

    # Select only columns to report (only include columns that exist in the dataframe)
    columns_of_interest = [col for col in column_mapping.keys() if col in df.columns]
    stats_df = df[columns_of_interest].agg(['mean', 'median', 'std'])

    result = []
    for col in columns_of_interest:
        result.append({
            "name": column_mapping[col],
            "mean": round(stats_df[col]["mean"], 3),
            "median": round(stats_df[col]["median"], 3),
            "std": round(stats_df[col]["std"], 3)
        })

    return result

@require_http_methods(["GET"])
def get_metadata_summary(request):
    session_name = request.GET.get("session_name")
    run_number = request.GET.get("run_number")

    if not session_name or not run_number:
        return JsonResponse({"error": "Missing session_name or run_number"}, status=400)

    base_proc_dir = f"{METADATA_SUMMARY_PATH}{session_name}/{run_number}/"
    metrics_path = os.path.join(base_proc_dir, "TiltSeries_Metrics.csv")
    timestamp_path = os.path.join(base_proc_dir, "TiltSeries_TimeStamp.csv")

    try:
        # Create a persistent SSH connection with optimized parameters
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Add connection optimization parameters
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
        ssh.connect(**ssh_config)
        
        # Create SFTP client with optimized buffer sizes
        sftp = ssh.open_sftp()
        sftp.get_channel().settimeout(10)
        sftp.get_channel().set_combine_stderr(True)

        try:
            # Combine all file operations into a single batch
            infra_start = time.time()
            try:
                # Use stat instead of listdir for faster checks
                try:
                    sftp.stat(metrics_path)
                    sftp.stat(timestamp_path)
                except FileNotFoundError:
                    return JsonResponse({"error": "Required files not found"}, status=404)
                
            except Exception as dir_err:
                return JsonResponse({"error": f"Access error: {str(dir_err)}"}, status=404)
            infra_time = time.time() - infra_start

            # Optimize file fetching with larger buffer size and parallel reading
            fetch_start = time.time()
            metrics_content = None
            timestamp_content = None
            
            # Read files with larger buffer size
            with sftp.open(metrics_path, 'r', bufsize=32768) as metrics_file:
                metrics_content = metrics_file.read().decode('utf-8')
            
            # Process metrics immediately while timestamp is being read
            df = pd.read_csv(StringIO(metrics_content))
            df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)
            
            # Note: Defocus(A) column is optional - if not present, it will be skipped in statistics

            # Use natural sort with optimized key function
            df = df.sort_values(by="Tilt_Series", key=lambda col: pd.Index([int(''.join(c for c in str(x) if c.isdigit()) or 0) for x in col])).reset_index(drop=True)
            fetch_time = time.time() - fetch_start

            # Compute statistics with optimized operations
            compute_start = time.time()
            computed_metrics = compute_stats(df)
            compute_time = time.time() - compute_start

            data_collection_dir = f"{DATA_COLLECTION_PATH}{session_name}/{run_number}/"
            aretomo3_processing_dir = f"{ARETOMO3_PROCESSING_PATH}{session_name}/{run_number}/"

            #Get User, Project, and grid information
            user_name=None
            project_name=None
            grid_name=None
            try:
                try:
                    session = MsiSession.objects.get(name=session_name)
                    logger.info(f"Session: {session}")

                    #Get User name
                    if session.user:
                        user_name = session.user.username
                    # Get Project name
                    if session.project:
                        project_name = session.project.name
                    
                    # Get Grid name
                    if session.grid:
                        grid_name = session.grid.name
                except MsiSession.DoesNotExist:
                    # Session not found, leave the values as None
                    logger.warning(f"No MsiSession found with name: {session_name}")
            except Exception as e:
                logger.warning(f"Error retrieving related information: {str(e)}")
                
                

            response = {
                "session_name": session_name,
                "run_number": run_number,
                "num_tomograms": len(df),
                "pixel_size": df["Pix_Size(A)"][0],
                "data_collection_directory": data_collection_dir,
                "aretomo3_processing_directory": aretomo3_processing_dir,
                "computed_metrics": computed_metrics,
                "user_name": user_name,
                "project_name": project_name,
                "grid_name": grid_name, 
                "timing": {
                    "infra_access_sec": round(infra_time, 3),
                    "file_fetch_sec": round(fetch_time, 3),
                    "data_compute_sec": round(compute_time, 3),
                }
            }

            return JsonResponse(response, json_dumps_params={"indent": 2})

        finally:
            sftp.close()
            ssh.close()

    except Exception as e:
        logger.error(f"Error processing metadata: {str(e)}")
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)


"""
Metadata Vizdata
"""

# Helper functions to calculate(min and max) metric ranges
def calculate_metric_ranges(df: pd.DataFrame) -> dict[str, list[float]]:
     # Get pixel size for conversion to Ångströms
    pixel_size = df['Pix_Size(A)'].iloc[0]

    # Create temporary columns with Ångström values
    df['Thickness(A)'] = df['Thickness(Pix)'] * pixel_size
    df['Global_Shift(A)'] = df['Global_Shift(Pix)'] * pixel_size
    column_mapping = {
        'Thickness(A)': 'thickness',
        'Tilt_Axis': 'tilt_axis',
        'Global_Shift(A)': 'global_shift',
        'Bad_Patch_Low': 'bad_patch_low',
        'Bad_Patch_All': 'bad_patch_all',
        'CTF_Res(A)': 'ctf_resolution',
        'CTF_Score': 'ctf_score',
        'Defocus(A)': 'defocus',
        'ExtPhase(Deg)': 'extphase',
        'Pix_Size(A)': 'pixel_size',
        'Alpha0': 'alpha0',
        'Beta0': 'beta0'
    }
    
    ranges = {}
    for csv_column, metric_name in column_mapping.items():
        # Only include defocus if the column exists
        if csv_column == 'Defocus(A)' and csv_column not in df.columns:
            continue
        if csv_column == 'ExtPhase(Deg)' and csv_column not in df.columns:
            continue
        if csv_column in df.columns:
            if csv_column == 'Defocus(A)':
                # Handle Defocus(A) column - it might be 0 if not present in original CSV
                try:
                    # Check if all values are 0 (indicating it was added as default)
                    if df[csv_column].eq(0).all():
                        ranges[metric_name] = [0, 0]
                    else:
                        # Extract the first number from each space-separated value
                        clean_values = df[csv_column].apply(lambda x: float(str(x).strip().split()[0]))
                        ranges[metric_name] = [float(clean_values.min()), float(clean_values.max())]
                except Exception as e:
                    logger.error(f"Error processing {csv_column}: {str(e)}")
                    # Fallback to default range if processing fails
                    ranges[metric_name] = [0, 0]
            elif csv_column == 'ExtPhase(Deg)':
                try:
                    # Check if all values are 0 (indicating it was added as default)
                    if df[csv_column].eq(0).all():
                        ranges[metric_name] = [0, 0]
                    else:
                        ranges[metric_name] = [float(df[csv_column].min()), float(df[csv_column].max())]
                except Exception as e:
                    logger.error(f"Error processing {csv_column}: {str(e)}")
                    # Fallback to default range if processing fails
                    ranges[metric_name] = [0, 0]
            else:
                ranges[metric_name] = [float(df[csv_column].min()), float(df[csv_column].max())]
    return ranges

# Helper function to apply filters
def apply_filters(df, filter_config):
    """
    Apply filters to the dataframe based on filter type (AND/OR) and filter criteria
    Returns both accepted and rejected dataframes
    """
 # If no filter config or empty filters, return entire dataset
    if not filter_config or 'filters' not in filter_config:
        return df, pd.DataFrame(columns=df.columns)

    filters = filter_config['filters']
    filter_type = filter_config.get('filter_type', 'AND')

    if not filters:
        return df, pd.DataFrame(columns=df.columns)
        
    # Map the filter field names to CSV column names
    column_mapping = {
            'thickness': 'Thickness(A)',
            'tilt_axis': 'Tilt_Axis',
            'global_shift': 'Global_Shift(A)',
            'bad_patch_low': 'Bad_Patch_Low',
            'bad_patch_all': 'Bad_Patch_All',
            'ctf_resolution': 'CTF_Res(A)',
            'ctf_score': 'CTF_Score',
            'defocus': 'Defocus(A)',
            'extphase': 'ExtPhase(Deg)',
            'alpha0': 'Alpha0',
            'beta0': 'Beta0'
    }
        
    mask = None
    for field, range_values in filters.items():
        if field not in column_mapping or len(range_values) != 2:
            continue
            
        column_name = column_mapping[field]
        
        # Skip defocus filter if the column doesn't exist (since all values are 0)
        if field == 'defocus' and column_name not in df.columns:
            continue
        
        # Skip defocus filter if the column doesn't exist (since all values are 0)
        if field == 'extphase' and column_name not in df.columns:
            continue
            
        min_val, max_val = range_values
        current_mask = (df[column_name] >= min_val) & (df[column_name] <= max_val)
        
        if mask is None:
            mask = current_mask
        else:
            if filter_type == 'AND':
                mask = mask & current_mask
            else:  # OR
                mask = mask | current_mask
    
    if mask is None:
        return df, pd.DataFrame(columns=df.columns)
        
    accepted_df = df[mask]
    rejected_df = df[~mask]
    
    return accepted_df, rejected_df

def natural_position_sort_key(name):
    """
    Custom sort key function for position names.
    Handles names like Position_1, Position_1_1, Position_1_2, etc.
    """
    # Remove 'Position_' prefix and split by underscore
    parts = name.replace('Position_', '').split('_')
    
    # Convert each part to integer, defaulting to 0 if conversion fails
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(0)
    
    # Pad with zeros to ensure consistent sorting (for cases with different depths)
    while len(numbers) < 3:  # Support up to Position_X_Y_Z
        numbers.append(0)
        
    return numbers

@require_http_methods(["GET"])
def get_metadata_viz_data(request):
    try:
        # Get request parameters
        session_name = request.GET.get("session_name")
        run_number = request.GET.get("run_number")
        q = request.GET.get("q",{})

        # Get sorting parameters
        sort_by = request.GET.get("sort_by", None)
        sort_direction = request.GET.get("sort_direction", "asc")

        if not session_name or not run_number:
            return JsonResponse({"error": "Missing session_name or run_number"}, status=400)


        # Parse filters if provided
        filter_config = json.loads(q) if q else {}

        # Read the CSV file 
        base_proc_dir = f"{METADATA_SUMMARY_PATH}{session_name}/{run_number}/"
        metrics_path = os.path.join(base_proc_dir, "TiltSeries_Metrics.csv")
        timestamp_path = os.path.join(base_proc_dir, "TiltSeries_TimeStamp.csv")

        thumbnail_base_url = os.path.join(HOSTNAME, session_name, run_number, "thumbnails/")
        ctf_base_url = os.path.join(HOSTNAME, session_name, run_number, "ctf_thumbnails/")
        print(metrics_path)
        print(timestamp_path)
        
        
        merged_df = preprocess_csv(metrics_path, timestamp_path, thumbnail_base_url, ctf_base_url, merge="continue")
        print(merged_df)
        
        # Create a persistent SSH connection with optimized parameters
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Add connection optimization parameters
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
        
        ssh.connect(**ssh_config)
       
        # Create SFTP client with optimized buffer sizes
        sftp = ssh.open_sftp()
        sftp.get_channel().settimeout(10)
        sftp.get_channel().set_combine_stderr(True)

        try:
            # Combine all file operations into a single batch
            infra_start = time.time()
            try:
                # Use stat instead of listdir for faster checks
                try:
                    sftp.stat(metrics_path)
                except FileNotFoundError:
                    return JsonResponse({"error": "Required files not found"}, status=404)
            except Exception as dir_err:
                return JsonResponse({"error": f"Access error: {str(dir_err)}"}, status=404)
            
            infra_time = time.time() - infra_start

            # Optimize file fetching with larger buffer size and parallel reading
            fetch_start = time.time()
            metrics_content = None
            timestamp_content = None
            
            # Read files with larger buffer size
            with sftp.open(metrics_path, 'r', bufsize=32768) as metrics_file:
                metrics_content = metrics_file.read().decode('utf-8')
            
            # Process metrics immediately while timestamp is being read
            df = pd.read_csv(StringIO(metrics_content))
            logger.info(f"Total positions in CSV before filtering: {len(df)}")

            # Required columns (excluding Defocus(A) and ExtPhase(Deg) which are optional)
            required_columns = [
                'Tilt_Series', 'Thickness(Pix)', 'Tilt_Axis', 'Global_Shift(Pix)',
                'Bad_Patch_Low', 'Bad_Patch_All', 'CTF_Res(A)', 'CTF_Score',
                 'Pix_Size(A)', 'Alpha0', 'Beta0'
            ]

            # Check for missing required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")

            # Add Defocus(A) column if it doesn't exist (set to 0)
            if 'Defocus(A)' not in df.columns:
                df['Defocus(A)'] = 0
                logger.info("Defocus(A) column not found in CSV, setting to 0")

            #  Add ExtPhase column if it doesn't exist (set to 0)
            if 'ExtPhase(Deg)' not in df.columns:
                 df['ExtPhase(Deg)'] = 0
                 logger.info("ExtPhase(Deg) column not found in CSV, setting to 0")

            df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)

            # Add thumbnail paths directly to the dataframe
            df["thumbnail_path"] = df["Tilt_Series"].apply(
                lambda ts: f"{thumbnail_base_url}{ts}.jpeg"
            )
            df["ctf_thumbnails_path"] = df["Tilt_Series"].apply(
                lambda ts: f"{ctf_base_url}{ts}.jpeg"
            )

            # Use the new custom sorting function
            df = df.sort_values(
                by="Tilt_Series",
                key=lambda col: col.map(natural_position_sort_key)
            ).reset_index(drop=True)
            fetch_time = time.time() - fetch_start
        
            # Calculate metric ranges before applying filters
            metric_ranges = calculate_metric_ranges(df)
        
            # Apply filters if provided
            accepted_df, rejected_df = apply_filters(df, filter_config)
        
        
            # Prepare the result lists for both accepted and rejected
            def prepare_result_list(df, apply_sorting=False):
                if df is None or df.empty:
                    return []
                result = []
                for _, row in df.iterrows():
                    item_name = str(row['Tilt_Series'])
                    image_path = row.get('thumbnail_path', None)
                    ctf_path = row.get('ctf_thumbnails_path', None)
            
                    item_image_path_to_return = image_path
                    ctf_thumbnails_path = ctf_path
                    if image_path is not None:
                        logger.info(f"[METADATA_VIZ_DEBUG] Item: {item_name}, Raw 'thumbnail_path' from row.get(): '{image_path}' (type: {type(image_path)})")
                    else:
                        logger.info("[METADATA_VIZ_DEBUG] 'thumbnail_path' column MISSING in df passed to prepare_result_list.")

                    if ctf_path is not None:
                        logger.info(f"[METADATA_VIZ_DEBUG] Item: {item_name}, Raw 'ctf_thumbnails_path' from row.get(): '{ctf_path}' (type: {type(ctf_path)})")
                    else:
                        logger.info("[METADATA_VIZ_DEBUG] 'ctf_thumbnails_path' column MISSING in df passed to prepare_result_list.")
                    metrics = {
                        'thickness': float(row['Thickness(A)']),
                        'tilt_axis': float(row['Tilt_Axis']),
                        'global_shift': float(row['Global_Shift(A)']),
                        'bad_patch_low': float(row['Bad_Patch_Low']),
                        'bad_patch_all': float(row['Bad_Patch_All']),
                        'ctf_resolution': float(row['CTF_Res(A)']),
                        'ctf_score': float(row['CTF_Score']),
                        'defocus': float(row['Defocus(A)']),
                        'extphase': float(row['ExtPhase(Deg)']),
                        'pixel_size': float(row['Pix_Size(A)']),
                        'alpha0': float(row['Alpha0']),
                        'beta0': float(row['Beta0']) if not pd.isna(row['Beta0']) else float('nan')
                    }
                    result.append({
                        'name': item_name,
                        'metrics': metrics,
                        'thumbnail_path': item_image_path_to_return,
                        'ctf_path': ctf_thumbnails_path
                    })
                
                # Apply sorting if requested
                if apply_sorting and sort_by and sort_by != 'Select Metric':
                    # Map frontend metric names to the actual keys in the metrics dictionary
                    metric_key_mapping = {
                        'thickness': 'thickness',
                        'tilt_axis': 'tilt_axis',
                        'global_shift': 'global_shift',
                        'bad_patch_low': 'bad_patch_low',
                        'bad_patch_all': 'bad_patch_all',
                        'ctf_resolution': 'ctf_resolution',
                        'ctf_score': 'ctf_score',
                        'defocus': 'defocus',
                        'extphase': 'extphase',
                        'alpha0': 'alpha0',
                        'beta0': 'beta0'
                    }
                    
                    metric_key = metric_key_mapping.get(sort_by, None)
                    if metric_key:
                        # Sort by the selected metric
                        result.sort(
                            key=lambda x: x['metrics'].get(metric_key, 0),
                            reverse=(sort_direction.lower() == 'desc')
                        )
                
                return result

            accepted_results = prepare_result_list(accepted_df, apply_sorting=True)
            rejected_results = prepare_result_list(rejected_df)

            # If no filters were applied, use the entire dataset as the result
            has_filters = filter_config and 'filters' in filter_config and filter_config['filters']
            if not has_filters:
                result = prepare_result_list(df, apply_sorting=True)
            else:
                result = []


            # The final response
            response_data = {
                'session_name': session_name,
                'run_number': run_number,
                'total_accepted': len(accepted_results),
                'total_rejected': len(rejected_results),
                'filters_applied': {
                    'filters': filter_config.get('filters'),
                    'filter_type': filter_config.get('filter_type', 'AND').upper()
                },
                'metric_ranges': metric_ranges,
                'accepted_results': accepted_results,
                'rejected_results': rejected_results
            }
            
            return JsonResponse(response_data, json_dumps_params={"indent": 2})

        finally:
            sftp.close()
            ssh.close()

    except Exception as e:
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)


   
@csrf_exempt
def get_plan_id(request):
    if request.method == 'GET':
        plan_name = request.GET.get('plan_name')
        if not plan_name:
            return JsonResponse({'error': 'Plan name not provided'}, status=400)
        
        try:
            plan = ProcPlan.objects.get(name=plan_name)
            return JsonResponse({'plan_id': plan.id})
        except ProcPlan.DoesNotExist:
            return JsonResponse({'error': f'Plan {plan_name} not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def get_msisession_id(request):
    if request.method == 'GET':
        session_name = request.GET.get('session_name')
        if not session_name:
            return JsonResponse({'error': 'Session name not provided'}, status=400)
        
        try:
            session = MsiSession.objects.get(name=session_name)
            return JsonResponse({'session_id': session.id})
        except MsiSession.DoesNotExist:
            return JsonResponse({'error': f'Session {session_name} not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
# @login_required
@require_http_methods(["POST"])
def trigger_syncer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_name = data.get('session_name')
            run_number = data.get('run_number')
            job_id = data.get('job_id')
            syncer_type = data.get('syncer_type', 'aretomo3')  # Default to aretomo3

            if not session_name or not run_number:
                return JsonResponse({'error': 'Missing session_name or run_number'}, status=400)

            # Determine which syncer script to use
            if syncer_type == 'denoise':
                syncer_script = 'denoise_syncer.py'
            else:
                syncer_script = 'aretomo3_syncer.py'

            syncer_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'processes', 'scripts', syncer_script)
            
            # Run the syncer with job tracking and continuous mode
            subprocess.Popen(['python', syncer_script_path, 
                            '--session', session_name,
                            '--run', run_number,
                            '--job-id', job_id if job_id else '',
                            '--continuous'],  # Add continuous mode
                           env=dict(os.environ, 
                                  PYTHONPATH=os.path.dirname(os.path.dirname(__file__))))
            
            logger.info(f"Started {syncer_type} syncer for session {session_name}, run {run_number}, tracking job {job_id}")
            
            return JsonResponse({
                'message': f'{syncer_type.capitalize()} syncer started successfully',
                'session': session_name,
                'run': run_number,
                'job_id': job_id,
                'status': 'running'
            })

        except Exception as e:
            logger.error(f"Failed to start syncer: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)