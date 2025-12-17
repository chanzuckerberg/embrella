"""
AreTomo3 processing workflow views.

These views handle submission and management of AreTomo3 tomographic
reconstruction jobs on the compute clusters.
"""

import base64
import logging
import os
import re
import subprocess

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import MsiSession, ProcPlan, ProcRun
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from umbrella_logger import logger

from common import clusterio
from common.clusterio import jsonify

from workflow.agent import Aretomo3
from workflow.views.constants import (
    ARETOMO3_BASIC_TEMPLATE_PATH,
    ARETOMO3_SCRIPT_PATH,
    ARETOMO3_TEMPLATE_PATH,
    KEYS,
)
from workflow.views.utils import store_log


@extend_schema(
    methods=["GET"],
    description="Fetches parsed Aretomo3 JSON metadata for a given session and run ID.",
    parameters=[
        OpenApiParameter(name="session", required=True, type=OpenApiTypes.STR, description="Session name (e.g. 23sep23a)"),
        OpenApiParameter(name="run_id", required=True, type=OpenApiTypes.STR, description="Run ID (e.g. 001)"),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@login_required
def get_aretomo3_json(request):
    """Fetch and parse AreTomo3 session JSON metadata."""
    session_name = request.GET.get("session")
    run_id = request.GET.get("run_id")

    if not session_name or not run_id:
        error_msg = "Session name and run ID are required."
        logger.error(error_msg)
        return JsonResponse({"error": error_msg}, status=400)

    remote_path = f"/hpc/projects/group.czii/krios1.processing/aretomo3/{session_name}/run{run_id}/AreTomo3_Session.json"

    try:
        json_data = clusterio.ssh_connect(remote_path)
        full_data = jsonify(json_data)

        # Extract version and gain
        version = full_data["software"]["version"]
        gain = full_data["input"]["Gain"]

        # Extract other parameters
        parsed_data = clusterio.extract_parameters(full_data, KEYS)

        # Insert version and gain at the beginning
        ordered_parsed_data = {"Version": version, "Gain": gain, **parsed_data}

        return JsonResponse(ordered_parsed_data, safe=False)
    except FileNotFoundError:
        error_msg = "File not found"
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
        "required": ["project_name", "use_old_gain", "user_id", "password"],
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        422: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@login_required
@csrf_exempt
def run_aretomo3_advanced(request):
    """Submit advanced AreTomo3 job with customizable parameters."""
    data_sanitized = {}  # Initialize this variable at the start
    if request.method == "POST":
        data = request.data  # json.loads(request.body)

        project_name = data.get("project_name")
        use_old_gain = data.get("use_old_gain")  # "yes" or "no"
        user_id = data.get("user_id")
        encoded_password = data.get("password", "")
        decoded_password = base64.b64decode(encoded_password).decode("utf-8")

        # Validate project_name format (e.g., 23sep23a)
        project_name_pattern = re.compile(r"^\d{2}[a-z]{3}\d{2}[a-z]$")
        if not project_name_pattern.match(project_name):
            return JsonResponse(
                {"error": "Invalid project_name format. Please check the project name: 422"},
                status=422,
            )
        data_sanitized = dict(data)
        data_sanitized.pop("password", None)
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
            if use_old_gain == "yes":
                gain_file_name = data.get("gain_file_name")
                run_number = data.get("run_number")
                denoiset_training = data.get("denoiset_training")
                pixel_size = data.get("pixel_size")
                use_advanced_params = data.get("use_advanced_params")
                dose_number = data.get("dose_number")
                frame_dose = data.get("frame_dose")  # Changed from num_checks to frame_dose
                # Only parse advanced params if user selected "yes"
                if use_advanced_params == "yes":
                    tilt_axis = data.get("tilt_axis", "")
                    tilt_axis_refine = data.get("tilt_axis_refine")
                    align_z = data.get("align_z", "")
                    vol_z = data.get("vol_z", "")
                    imod_option = data.get("imod_option")
                    local_shift = data.get("local_shift")
                    tilt_offset = data.get("tilt_offset")
                    thickness_mesaure = data.get("thickness_measure")

            # Branch: no old gain
            elif use_old_gain == "no":
                run_number = data.get("run_number")
                denoiset_training = data.get("denoiset_training")
                pixel_size = data.get("pixel_size")
                use_advanced_params = data.get("use_advanced_params")
                dose_number = data.get("dose_number")
                frame_dose = data.get("frame_dose")  # Changed from num_checks to frame_dose

                if use_advanced_params == "yes":
                    tilt_axis = data.get("tilt_axis", "")
                    tilt_axis_refine = data.get("tilt_axis_refine")
                    align_z = data.get("align_z", "")
                    vol_z = data.get("vol_z", 1200)
                    imod_option = data.get("imod_option")
                    local_shift = data.get("local_shift")
                    tilt_offset = data.get("tilt_offset")
                    thickness_mesaure = data.get("thickness_measure")

            else:
                return JsonResponse(
                    {"error": 'Invalid use_old_gain value. Must be "yes" or "no": 422'},
                    status=422,
                )

            # Check if run number already exists in the database
            try:
                # Get the session and plan (project_name is the same as session_name in this context)
                msi_session = MsiSession.objects.get(name=project_name)
                proc_plan = ProcPlan.objects.get(name="czii-live")  # AreTomo3 uses czii-live plan

                # Ensure the run number has the correct format (e.g., "run001")
                if not run_number.startswith("run"):
                    run_number = f"run{run_number.zfill(3)}"

                # Check if this run number already exists for this session and plan
                existing_run = ProcRun.objects.filter(
                    name=run_number,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
                ).first()

                if existing_run:
                    return JsonResponse(
                        {
                            "error": f"Run number {run_number} already exists for session {project_name}. Please choose a different run number.",
                        },
                        status=400,
                    )

            except MsiSession.DoesNotExist:
                return JsonResponse({"error": f"Session {project_name} not found in database"}, status=404)
            except ProcPlan.DoesNotExist:
                return JsonResponse({"error": "AreTomo3 processing plan (czii-live) not found"}, status=404)

            # Store user credentials in session
            request.session["user_id"] = user_id
            request.session["decoded_password"] = decoded_password

            # Initialize the Aretomo3 object and connect
            aretomo = Aretomo3(
                cluster_id="czii",
                auth={"username": user_id, "password": decoded_password},
                remote_script_dir=ARETOMO3_SCRIPT_PATH,
                local_template_path=ARETOMO3_BASIC_TEMPLATE_PATH,
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
                denoiset_training,
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
                user_id=user_id,
            )

            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            print(found_ids)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Store log regardless of success or failure
            store_log(
                job_name="Aretomo3",
                request=request,
                data_sanitized=data_sanitized,
                error=None,
                advanced_status=True,
                job_id=job_id_str,
            )

            # Return your response
            return JsonResponse(
                {
                    "message": f"Advanced job for project {project_name} submitted successfully.",
                    "output": output,
                    "error": error,
                    "job_id": job_id_str,
                },
            )

        except Exception as e:
            logger.error(f"Error in run_aretomo3_advanced: {str(e)}")
            store_log(
                job_name="Aretomo3",
                request=request,
                data_sanitized=data_sanitized,
                error=str(e),
                advanced_status=True,
                job_id=None,
            )
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            # Ensure we always close the connection if we opened it
            if "aretomo" in locals():
                aretomo.close()

    # Handle invalid request method
    return JsonResponse({"error": "Invalid request method: 400"}, status=400)


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
        "required": ["session_name", "run_number", "pixel_size", "total_dose", "num_checks", "user_id", "password"],
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        422: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@login_required
@csrf_exempt
def run_aretomo3(request):
    """Submit standard AreTomo3 job."""
    if request.method == "POST":
        data = request.data
        session_name = data.get("session_name")
        run_number = data.get("run_number")
        pix_size = data.get("pixel_size")
        total_dose = data.get("dose_number")
        frame_dose = data.get("frame_dose")  # Changed from num_checks to frame_dose
        user_id = data.get("user_id")
        encoded_password = data.get("password")
        decoded_password = base64.b64decode(encoded_password).decode("utf-8")

        # Validate session_name format
        session_name_pattern = re.compile(r"^\d{2}[a-z]{3}\d{2}[a-z]$")
        if not session_name_pattern.match(session_name):
            return JsonResponse(
                {"error": "Invalid session_name format. Please check the session name: 422"}, status=422,
            )

        # Check if run number already exists in the database
        try:
            # Get the session and plan
            msi_session = MsiSession.objects.get(name=session_name)
            proc_plan = ProcPlan.objects.get(name="czii-live")  # AreTomo3 uses czii-live plan

            # Ensure the run number has the correct format (e.g., "run001")
            if not run_number.startswith("run"):
                run_number = f"run{run_number.zfill(3)}"

            # Check if this run number already exists for this session and plan
            existing_run = ProcRun.objects.filter(
                name=run_number,
                msi_session=msi_session,
                proc_plan=proc_plan,
            ).first()

            if existing_run:
                return JsonResponse(
                    {
                        "error": f"Run number {run_number} already exists for session {session_name}. Please choose a different run number.",
                    },
                    status=400,
                )

        except MsiSession.DoesNotExist:
            return JsonResponse({"error": f"Session {session_name} not found in database"}, status=404)
        except ProcPlan.DoesNotExist:
            return JsonResponse({"error": "AreTomo3 processing plan (czii-live) not found"}, status=404)

        # Store user_id and decoded_password in session
        request.session["user_id"] = user_id
        request.session["decoded_password"] = decoded_password

        data_sanitized = dict(data)
        data_sanitized.pop("password", None)
        job_id_str = None

        try:
            aretomo = Aretomo3(
                cluster_id="czii",
                auth={"username": user_id, "password": decoded_password},
                remote_script_dir=ARETOMO3_SCRIPT_PATH,
                local_template_path=ARETOMO3_TEMPLATE_PATH,
            )
            # Connect to the remote server
            aretomo.connect()

            # Run the script and get the output
            output, error = aretomo.run_script(session_name, run_number, pix_size, total_dose, frame_dose, user_id)

            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            job_id_str = ",".join(str(int(id) + 1) for id in found_ids) if found_ids else None

            # Log success without an error message
            store_log(
                job_name="Aretomo3",
                request=request,
                data_sanitized=data_sanitized,
                error="",
                advanced_status=False,
                job_id=job_id_str,
            )

            # Trigger the AreTomo3 syncer script
            try:
                syncer_script_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "processes", "scripts", "aretomo3_syncer.py",
                )
                # Run the syncer once with job tracking
                subprocess.Popen(
                    [
                        "python",
                        syncer_script_path,
                        "--session",
                        session_name,
                        "--run",
                        run_number,
                        "--job-id",
                        job_id_str,
                        "--continuous",
                    ],
                    env=dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(__file__))),
                )
                logging.info(
                    f"Started AreTomo3 syncer for session {session_name}, run {run_number}, tracking job {job_id_str}",
                )
            except Exception as e:
                logging.error(f"Failed to start AreTomo3 syncer: {str(e)}")

            return JsonResponse(
                {
                    "message": f"Session {session_name} for Aretomo3 is submitted successfully. Please check the output directory below",
                    "output": output,
                    "error": error,
                    "job_id": job_id_str,
                },
            )
        except Exception as e:
            # Log the error details
            store_log(
                job_name="Aretomo3",
                request=request,
                data_sanitized=data_sanitized,
                error=str(e),
                advanced_status=False,
                job_id=job_id_str,
            )
            return JsonResponse({"error": str(e) + ": 500"}, status=500)
        finally:
            aretomo.close()
    else:
        # For non-POST requests, log the error and return a 400 status
        default_data = {}
        store_log(
            job_name="Aretomo3",
            request=request,
            data_sanitized=default_data,
            error="Invalid request method",
            advanced_status=False,
            job_id=None,
        )
        return JsonResponse({"error": "Invalid request method: 400"}, status=400)
