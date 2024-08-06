import logging
from .utils import jsonify, ssh_connect, extract_parameters
from django.http import JsonResponse
from django.shortcuts import render
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KEYS = ('PixSize',
        'AtBin',
        'CorrCTF',
        'McIter',
        'Wbp')


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
    # except Exception as e:
    #     error_msg = f"An unexpected error occurred: {e}"
    #     logger.error(error_msg)
    #     return JsonResponse({"error": error_msg}, status=500)


def custom_workflow_page(request):
    return render(request, 'workflows/workflow_page.html')


