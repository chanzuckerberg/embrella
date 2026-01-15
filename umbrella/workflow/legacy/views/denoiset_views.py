"""
DenoisET processing workflow views.

These views handle submission and management of DenoisET denoising jobs
on the compute clusters.
"""

import base64
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view

from workflow.agent import Denoiset
from workflow.views.constants import DENOISET_SCRIPT_PATH, DENOISET_TEMPLATE_PATH
from workflow.views.utils import store_log


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
            "live_denoising": {"type": "boolean", "default": False},
        },
        "required": ["session_name", "run_number", "model_name", "denoise_run_number", "user_id", "password"],
    },
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["POST"])
@login_required
@csrf_exempt
def run_denoiset(request):
    """Submit DenoisET denoising job."""
    if request.method == "POST":
        try:
            data = request.data  # json.loads(request.body)
            session_name = data.get("session_name")
            run_number = data.get("run_number")
            model_name = data.get("model_name")
            denoise_run_number = data.get("denoise_run_number")
            user_id = data.get("user_id")
            encoded_password = data.get("password")
            decoded_password = base64.b64decode(encoded_password).decode("utf-8")

            # Store user_id and decoded_password in session
            request.session["user_id"] = user_id
            request.session["decoded_password"] = decoded_password

            data_sanitized = dict(data)
            print(data_sanitized)
            data_sanitized.pop("password", None)

            # Create the Denoiset instance.
            denoiset = Denoiset(
                cluster_id="czii",
                auth={"username": user_id, "password": decoded_password},
                remote_script_dir=DENOISET_SCRIPT_PATH,
                local_template_path=DENOISET_TEMPLATE_PATH,
            )
            # Connect to the remote server.
            denoiset.connect()

            # Retrieve the live denoising flag; defaults to False if not provided.
            live_denoising = data.get("live_denoising", False)

            # Run the denoising script and get the output.
            output, error = denoiset.run_script(
                session_name, run_number, denoise_run_number, model_name, user_id, live_denoising,
            )

            # Extract the job ID(s) from the output.
            found_ids = re.findall(r"Submitted batch job (\d+)", output)
            job_id_str = ",".join(found_ids) if found_ids else None

            # Log the successful submission.
            store_log(
                job_name="DenoisET",
                request=request,
                data_sanitized=data_sanitized,
                error="",
                advanced_status=True,
                job_id=job_id_str,
            )

            return JsonResponse(
                {
                    "message": f"Session {session_name} for Denoiset is submitted successfully. Please check the output directory.",
                    "output": output,
                    "error": error,
                    "job_id": job_id_str,
                },
            )

        except Exception as e:
            # Log error details.
            store_log(
                job_name="DenoisET",
                request=request,
                data_sanitized=data_sanitized if "data_sanitized" in locals() else {},
                error=str(e),
                advanced_status=False,
                job_id=None,
            )
            return JsonResponse({"error": str(e) + ": 500"}, status=500)

        finally:
            # Ensure the SSH connection is closed.
            if "denoiset" in locals():
                denoiset.close()

    # For non-POST requests.
    store_log(
        job_name="DenoisET",
        request=request,
        data_sanitized={},
        error="Invalid request method",
        advanced_status=False,
        job_id=None,
    )
    return JsonResponse({"error": "Invalid request method: 400"}, status=400)
