from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters, hostname, port, username, password, ssh_file_exists, ssh_list_directory
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
from django.core.cache import cache
from workflow.utils import ssh_connect
import time
import pandas as pd
import paramiko
from io import StringIO
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
METADATA_SUMMARY_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/'
DATA_COLLECTION_PATH = '/hpc/instruments/czii.krios1/OffloadData/'
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
    
# @login_required
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


@login_required
@csrf_exempt
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

@csrf_exempt
@login_required
def user_info(request):
    username = request.user.username.split('@')[0]
    response_data = {"username": username}
    return JsonResponse(response_data, safe=False, status=200)

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

@require_http_methods(["GET"])
def get_msi_session_list(request):
    try:
        # Fetch only the name field from MsiSession
        session_names = list(MsiSession.objects.values_list('name', flat=True))
        
        return JsonResponse({'session_names': session_names}, status=200)

    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    
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


def preprocess_csv(metrics_path, timestamp_path, merge=False):
    try:
        # Load data from remote server using ssh_connect
        print(f"Attempting to read metrics file: {metrics_path}")
        metrics_content = ssh_connect(metrics_path)
        print(f"Successfully read metrics file")
        
        # Convert string content to pandas DataFrame
        metrics_df = pd.read_csv(StringIO(metrics_content))
        
        # Normalize
        metrics_df["Tilt_Series"] = metrics_df["Tilt_Series"].str.replace(".mrc", "", regex=False)
        
        # Sort Tilt_Series using natural sort
        metrics_df = metrics_df.sort_values(by="Tilt_Series", key=lambda col: col.map(natural_key)).reset_index(drop=True)
        
        if merge:
            print(f"Attempting to read timestamp file: {timestamp_path}")
            timestamp_content = ssh_connect(timestamp_path)
            print(f"Successfully read timestamp file")
            
            # Convert string content to pandas DataFrame
            timestamp_df = pd.read_csv(StringIO(timestamp_content))
            
            # Merge
            merged_df = pd.merge(timestamp_df, metrics_df, on="Tilt_Series", how="left")
            
            # Sort Tilt_Series using natural sort
            merged_df = merged_df.sort_values(by="Tilt_Series", key=lambda col: col.map(natural_key)).reset_index(drop=True)
            
            return merged_df
        else:
            return metrics_df
            
    except Exception as e:
        print(f"Error in preprocess_csv: {str(e)}")
        raise


def compute_stats(df: pd.DataFrame) -> list:
    column_mapping = {
        'CTF_Score': 'CTF',
        'CTF_Res(A)': 'Resolution',
        'Global_Shift(Pix)': 'Defocus',
        'Thickness(Pix)': 'Tilt Angle',
        'Tilt_Axis': 'Tilt Axis',
        'Global_Shift(Pix)': 'Global Shift',
        'Bad_Patch_Low': 'Bad Patch Low',
        'Bad_Patch_All': 'Bad Patch All',
    }

    # Select only columns to report
    columns_of_interest = list(column_mapping.keys())
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
            
            # Use natural sort with optimized key function
            df = df.sort_values(by="Tilt_Series", key=lambda col: pd.Index([int(''.join(c for c in str(x) if c.isdigit()) or 0) for x in col])).reset_index(drop=True)
            fetch_time = time.time() - fetch_start

            # Compute statistics with optimized operations
            compute_start = time.time()
            computed_metrics = compute_stats(df)
            compute_time = time.time() - compute_start

            data_collection_dir = f"{DATA_COLLECTION_PATH}{session_name}/{run_number}/"
            aretomo3_processing_dir = f"{ARETOMO3_PROCESSING_PATH}{session_name}/{run_number}/"

            response = {
                "session_name": session_name,
                "run_number": run_number,
                "data_collection_directory": data_collection_dir,
                "aretomo3_processing_directory": aretomo3_processing_dir,
                "computed_metrics": computed_metrics,
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
    column_mapping = {
        'Thickness(Pix)': 'thickness_pix',
        'Tilt_Axis': 'tilt_axis',
        'Global_Shift(Pix)': 'global_shift_pix',
        'Bad_Patch_Low': 'bad_patch_low',
        'Bad_Patch_All': 'bad_patch_all',
        'CTF_Res(A)': 'ctf_resolution_a',
        'CTF_Score': 'ctf_score',
        'DF_Hand': 'df_hand',
        'Pix_Size(A)': 'pixel_size_a',
        'Cs(nm)': 'cs_nm',
        'Kv': 'kv',
        'Alpha0': 'alpha0',
        'Beta0': 'beta0'
    }
    
    ranges = {}
    for csv_column, metric_name in column_mapping.items():
        if csv_column in df.columns:
            ranges[metric_name] = [float(df[csv_column].min()), float(df[csv_column].max())]
    
    return ranges

# Helper function to apply filters
def apply_filters(df, filters):
    filtered_df = df.copy()
    
    for field, range_values in filters.items():
        if len(range_values) != 2:
            continue
            
        min_val, max_val = range_values
        
        # Map the filter field names to CSV column names
        column_mapping = {
            'thickness_pix': 'Thickness(Pix)',
            'tilt_axis': 'Tilt_Axis',
            'global_shift_pix': 'Global_Shift(Pix)',
            'bad_patch_low': 'Bad_Patch_Low',
            'bad_patch_all': 'Bad_Patch_All',
            'ctf_resolution_a': 'CTF_Res(A)',
            'ctf_score': 'CTF_Score',
            'df_hand': 'DF_Hand',
            'pixel_size_a': 'Pix_Size(A)',
            'cs_nm': 'Cs(nm)',
            'kv': 'Kv',
            'alpha0': 'Alpha0',
            'beta0': 'Beta0'
        }
        
        if field in column_mapping:
            column_name = column_mapping[field]
            filtered_df = filtered_df[
                (filtered_df[column_name] >= min_val) & 
                (filtered_df[column_name] <= max_val)
            ]
    
    return filtered_df

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

        # Pagination parameters
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 15))
        
        if page < 1:
            return JsonResponse({"error": "Page number must be greater than 0"}, status=400)
        if page_size < 1:
            return JsonResponse({"error": "Page size must be greater than 0"}, status=400)

        if not session_name or not run_number:
            return JsonResponse({"error": "Missing session_name or run_number"}, status=400)


        # Parse filters if provided
        filters = json.loads(q) if q else None

        # Read the CSV file 
        base_proc_dir = f"{METADATA_SUMMARY_PATH}{session_name}/{run_number}/"
        metrics_path = os.path.join(base_proc_dir, "TiltSeries_Metrics.csv")
        
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
            print(f"Total positions in CSV before filtering: {len(df)}")

            # Required column
            required_columns = [
                'Tilt_Series', 'Thickness(Pix)', 'Tilt_Axis', 'Global_Shift(Pix)',
                'Bad_Patch_Low', 'Bad_Patch_All', 'CTF_Res(A)', 'CTF_Score',
                'DF_Hand', 'Pix_Size(A)', 'Cs(nm)', 'Kv', 'Alpha0', 'Beta0', 'Tilt_Series'
            ]

            # for missing columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")

            df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)

            # Use the new custom sorting function
            df = df.sort_values(
                by="Tilt_Series",
                key=lambda col: col.map(natural_position_sort_key)
            ).reset_index(drop=True)
            fetch_time = time.time() - fetch_start
        
            # Calculate metric ranges before applying filters
            metric_ranges = calculate_metric_ranges(df)
        
            # Apply filters if provided
            if filters:
                df = apply_filters(df, filters)
        
            # Prepare the result list
            result = []
            for _, row in df.iterrows():
                metrics = {
                    'thickness_pix': float(row['Thickness(Pix)']),
                    'tilt_axis': float(row['Tilt_Axis']),
                    'global_shift_pix': float(row['Global_Shift(Pix)']),
                    'bad_patch_low': float(row['Bad_Patch_Low']),
                    'bad_patch_all': float(row['Bad_Patch_All']),
                    'ctf_resolution_a': float(row['CTF_Res(A)']),
                    'ctf_score': float(row['CTF_Score']),
                    'df_hand': float(row['DF_Hand']),
                    'pixel_size_a': float(row['Pix_Size(A)']),
                    'cs_nm': float(row['Cs(nm)']),
                    'kv': float(row['Kv']),
                    'alpha0': float(row['Alpha0']),
                    'beta0': float(row['Beta0'])
                }
                result.append({
                    'name': str(row['Tilt_Series']),
                    'metrics': metrics
                })
            
            # Calculate pagination values
            total_items = len(result)
            total_pages = (total_items + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_items)
            
            # Slice the results for the current page
            paginated_result = result[start_idx:end_idx]


            # The final response
            response_data = {
                'session_name': session_name,
                'run_number': run_number,
                'num_tomograms': len(result),
                'filters_applied': filters if filters else None,
                'metric_ranges': metric_ranges,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'total_items': total_items
                },
                'result': paginated_result
            }
         
            print(f"Result length: {len(result)}")
            return JsonResponse(response_data, json_dumps_params={"indent": 2})
        finally:
            sftp.close()
            ssh.close()

    except Exception as e:
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)