from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters
from django.http import JsonResponse
from django.shortcuts import render
from .agent import Aretomo3
from umbrella.settings import ARETOMO3_SCRIPT_PATH, ARETOMO3_ADVANCED_PATH
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
from django.db.models import F

KEYS = ('PixSize',
        'AtBin',
        'CorrCTF',
        'McBin',
        'Wbp')
# HOST = '10.50.120.52'
# HOST = 'login-1.czii.org'
HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')

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
        parsed_data = extract_parameters(full_data, KEYS)
        print(parsed_data)
        return JsonResponse(parsed_data, safe=False)
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
                thickness_mesaure=thickness_mesaure
            )

            # Return your response

            return JsonResponse({
                'message': f'Session {project_name} for Advanced Aretomo3 is submitted successfully. Please check the below output directory',
                'output': output,
                'error': error
            })


        except Exception as e:
            logger.error(f'Error in run_aretomo3_advanced: {str(e)}')
            return JsonResponse({'error': str(e)}, status=500)

        finally:
            # Ensure we always close the connection if we opened it
            if 'aretomo' in locals():
                aretomo.close()

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

        try:
            aretomo = Aretomo3(HOST, PORT, user_id, decoded_password, ARETOMO3_SCRIPT_PATH)

            # Connect to the remote server
            aretomo.connect()

            # Run the script and get the output
            output, error = aretomo.run_script(session_name, run_number, pix_size, total_dose,num_checks, user_id)
            return JsonResponse({'message': f'Session {session_name} for Aretomo3 is submitted successfully. Please check the below output directory', 'output': output, 'error': error})
        except Exception as e:
            return JsonResponse({'error': str(e) + ': 500'}, status=500)
        finally:
            aretomo.close()

    return JsonResponse({'error': 'Invalid request method: 400'}, status=400)

@csrf_exempt
@login_required
def user_info(request):
    username = request.user.username.split('@')[0]
    response_data = {"username": username}
    return JsonResponse(response_data, safe=False, status=200)

@login_required
def cancel_aretomo3(request):
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
    if request.method == 'POST':
        data = json.loads(request.body)
        print(data)
        job_name = data.get('job_name')

        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH)

        try:
            # Connect to the remote server
            aretomo.connect()
            if job_name is None:
                output, error = aretomo.track_jobs(job_name=None,all=True)
            else:
                output, error = aretomo.track_jobs(job_name)
            formatted_output = format_job_output(output)
            return JsonResponse({'jobs': formatted_output})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            aretomo.close()

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
