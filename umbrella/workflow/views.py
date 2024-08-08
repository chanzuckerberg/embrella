from umbrella_logger import logger
from .utils import jsonify, ssh_connect, extract_parameters
from django.http import JsonResponse
from django.shortcuts import render
from .agent import ARETOMO3_SCRIPT_PATH, Aretomo3
import os
import json
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

from django.http import JsonResponse

def run_aretomo3(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_name = data.get('session_name')
        run_number = data.get('run_number')
        pix_size = data.get('pixel_size')
        num_checks = data.get('num_checks')
        seconds = data.get('seconds')
        user_id = data.get('user_id')

        # Create an instance of Aretomo3
        aretomo = Aretomo3(HOST, PORT, USERNAME, PASSWORD, ARETOMO3_SCRIPT_PATH)

        try:
            # Connect to the remote server
            aretomo.connect()

            # Run the script and get the output
            output, error = aretomo.run_script(session_name, run_number, pix_size, num_checks, seconds, user_id)
            return JsonResponse({'output': f'Session {session_name} for Aretomo3 is submitted successfully. Please check the below output directory'})

        finally:
            aretomo.close()

    return JsonResponse({'error': 'Invalid request method'}, status=400)



def custom_workflow_page(request):
    return render(request, 'workflows/workflow_page.html')

def custom_run_workflow_page(request):
    return render(request, 'workflows/workflow_run.html')