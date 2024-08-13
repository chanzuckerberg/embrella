from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters
from django.http import JsonResponse
from django.shortcuts import render
from .agent import Aretomo3
from umbrella.settings import ARETOMO3_SCRIPT_PATH
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
import os
import base64
import re
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.http import JsonResponse
# Configure logging


KEYS = ('PixSize',
        'AtBin',
        'CorrCTF',
        'McBin',
        'Wbp')
HOST = '10.50.120.52'
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')

@login_required
def get_aretomo3_json(request):
    session_name = request.GET.get('session')
    run_id = request.GET.get('run_id')
    vol_id = request.GET.get('vol_id')

    if not session_name or not run_id:
        error_msg = "Session name and run ID are required."
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=400)

    remote_path = f'/hpc/projects/group.czii/krios1.processing/aretomo3/{session_name}/run{run_id}/AreTomo3_Session.json'
    if vol_id:
        remote_path = f'/hpc/projects/group.czii/krios1.processing/aretomo3/{session_name}/run{run_id}/vol{vol_id}/AreTomo3_Session.json'

    try:
        json_data = ssh_connect(remote_path)
        full_data = jsonify(json_data)
        parsed_data = extract_parameters(full_data, KEYS)
        return JsonResponse(parsed_data, safe=False)
    except FileNotFoundError as fnf_err:
        error_msg = f"File not found"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=404)
    except Exception as err:
        error_msg = f"Please check the server status: {str(err)}"
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=500)



@login_required
@csrf_exempt
def run_aretomo3(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_name = data.get('session_name')
        run_number = data.get('run_number')
        pix_size = data.get('pixel_size')
        num_checks = data.get('num_checks')
        seconds = data.get('seconds')
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
            output, error = aretomo.run_script(session_name, run_number, pix_size, num_checks, seconds, user_id)
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

        if not user_id or not decoded_password:
            return JsonResponse({'error': 'User credentials not found in session'}, status=400)

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
        job_name = data.get('job_name')

        user_id = request.session.get('user_id')
        decoded_password = request.session.get('decoded_password')

        if not user_id or not decoded_password:
            return JsonResponse({'error': 'User credentials not found in session'}, status=400)

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