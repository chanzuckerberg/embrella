"""
Copick workflow views.

These views handle submission and management of Copick processing jobs,
including project creation, tomogram imports, template map queries, and
object addition to Copick processing runs.
"""

import base64
import os
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view
from umbrella_logger import logger

from common import clusterio
from common.clusterio import jsonify
from workflow.agent import RemoteJobSubmitter
from workflow.views.constants import (
    COPICK_ADD_OBJECT_TEMPLATE_PATH,
    COPICK_IMPORT_TOMO_TEMPLATE_PATH,
    COPICK_SCRIPT_DIR,
    COPICK_TEMPLATE_PATH,
)
from workflow.views.utils import store_log


@extend_schema(
    methods=["POST"],
    summary="Create CoPick project",
    description="Submits a remote Slurm job using the CoPick **create** template.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "session_name": {"type": "string", "example": "25sep18a"},
                "copick_run": {"type": "string", "example": "run003"},
                "import_tomo_type": {"type": "string", "example": "DCTF"},
                "import_tomogram_run": {"type": "string", "example": "run001"},
                "downsample_tomogram_voxel_size": {"type": "string", "nullable": True, "example": "12"},
                "user_id": {"type": "string", "example": "yyu"},
                "password": {"type": "string", "description": "Base64-encoded password", "example": "c2VjcmV0MTIz"},
            },
            "required": ["session_name", "copick_run", "import_tomo_type", "import_tomogram_run", "user_id"],
        },
    },
    responses={
        200: OpenApiResponse(
            description="Job submission succeeded",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "message": "Session 25sep18a: create_copick submitted.",
                        "output": "Submitted batch job 123456\nSubmitted batch job 123457\n",
                        "error": "",
                        "job_id": "123456,123457",
                    },
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Unhandled server error during submission",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Server error", value={"error": "Some traceback or error string: 500"}, response_only=True
                ),
            ],
        ),
    },
    tags=["workflow"],
)
@csrf_exempt
@api_view(["POST"])
# @login_required
def run_create_copick(request):
    """Submit Copick project creation job."""
    if request.method != "POST":
        store_log(
            job_name="CreateCopick",
            request=request,
            data_sanitized={},
            error="Invalid request method",
            advanced_status=False,
            job_id=None,
        )
        return JsonResponse({"error": "Invalid request method: 400"}, status=400)

    try:
        data = request.data  # json.loads(request.body)

        # Required fields (adjust names to match your frontend payload)
        session_name = data.get("session_name")  # e.g. "25sep18a"
        copick_run = data.get("copick_run")  # e.g. "run003"
        import_type = data.get("import_tomo_type")  # e.g. "DCTF"
        import_run = data.get("import_tomogram_run")  # e.g. "run001"

        # Optional
        downsample_vox = data.get("downsample_tomogram_voxel_size", "")

        # Auth
        user_id = data.get("user_id")
        encoded_password = data.get("password")  # base64 string from client
        decoded_password = base64.b64decode(encoded_password).decode("utf-8") if encoded_password else ""

        # Persist minimal auth in session (if you need it later)
        request.session["user_id"] = user_id
        request.session["decoded_password"] = decoded_password

        # Sanitize for logging
        data_sanitized = dict(data)
        data_sanitized.pop("password", None)

        # Build submitter
        submitter = RemoteJobSubmitter(
            cluster_id="bruno",
            auth={"username": user_id, "password": decoded_password},
            remote_script_dir=COPICK_SCRIPT_DIR,
        )
        submitter.connect()

        # Job name for the remote .sh
        job_name = f"{session_name}_create_copick_{copick_run}"

        # Render + submit. **Keys must match your Jinja placeholders.**
        out, err = submitter.run_script(
            template_path=COPICK_TEMPLATE_PATH,
            job_name=job_name,
            session=session_name,
            copickRun=copick_run,
            importTomoType=import_type,
            importTomogramRun=import_run,
            downsampleTomogramVoxelSize=downsample_vox,
        )

        # Extract Slurm job id(s)
        ids = re.findall(r"Submitted batch job (\d+)", out)
        job_id_str = ",".join(ids) if ids else None

        # Log success
        store_log(
            job_name="CreateCopick",
            request=request,
            data_sanitized=data_sanitized,
            error="",
            advanced_status=True,
            job_id=job_id_str,
        )

        return JsonResponse(
            {
                "message": f"Session {session_name}: create_copick submitted.",
                "output": out,
                "error": err,
                "job_id": job_id_str,
            },
        )

    except Exception as e:
        store_log(
            job_name="CreateCopick",
            request=request,
            data_sanitized=data_sanitized if "data_sanitized" in locals() else {},
            error=str(e),
            advanced_status=False,
            job_id=None,
        )
        return JsonResponse({"error": f"{e}: 500"}, status=500)

    finally:
        if "submitter" in locals():
            submitter.close()


@extend_schema(
    methods=["POST"],
    summary="Import tomograms into a CoPick procrun",
    description=(
        "Submits a remote Slurm job using the CoPick **import tomograms** template. "
        "Reads credentials and parameters from the JSON request body. "
        "`copick_run` may be provided as '003' or 'run003' and will be normalized server-side."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                # Auth
                "user_id": {"type": "string", "example": "yyu"},
                "password": {"type": "string", "description": "Base64-encoded password", "example": "c2VjcmV0MTIz"},
                # Required job params
                "session_name": {"type": "string", "example": "25sep18a"},
                "copick_run": {"type": "string", "example": "003"},
                "import_tomo_type": {
                    "type": "string",
                    "enum": ["dctf", "sart", "wbp", "denoise"],
                    "example": "dctf",
                },
                "import_tomogram_run": {"type": "string", "example": "run001"},
                # Optional
                "downsample_tomogram_voxel_size": {
                    "type": "string",
                    "nullable": True,
                    "example": "10",
                },
            },
            "required": [
                "user_id",
                "password",
                "session_name",
                "copick_run",
                "import_tomo_type",
                "import_tomogram_run",
            ],
        },
    },
    responses={
        200: OpenApiResponse(
            description="Job submission succeeded",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "message": "Session 25sep18a: copick import submitted.",
                        "output": "Submitted batch job 123456\n",
                        "error": "",
                        "job_id": "123456",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad request (missing fields or non-POST)",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Invalid method",
                    value={"error": "Invalid request method: 400"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Missing fields",
                    value={"error": "Missing fields: user_id, password"},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Unhandled server error during submission",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Server error",
                    value={"error": "Some traceback or error string: 500"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["workflow"],
)
@csrf_exempt
@api_view(["POST"])
@login_required
def run_import_tomogram_copick(request):
    """
    Submit a 'copick import tomograms' job via the remote template.

    Required JSON:
      - user_id
      - password (base64)
      - session_name        (Copick session)
      - copick_run          (e.g., 'run003' or '003')
      - import_tomo_type    ('dctf'|'sart'|'wbp'|'denoise')
      - import_tomogram_run (e.g., 'run001')
    Optional:
      - downsample_tomogram_voxel_size (e.g., '10')
    """
    if request.method != "POST":
        store_log(
            job_name="CopickImport",
            request=request,
            data_sanitized={},
            error="Invalid request method",
            advanced_status=False,
            job_id=None,
        )
        return JsonResponse({"error": "Invalid request method: 400"}, status=400)

    try:
        data = request.data  # json.loads(request.body)

        # -------- inputs --------
        session_name = (data.get("session_name") or "").strip()
        copick_run = (data.get("copick_run") or "").strip()
        import_type = (data.get("import_tomo_type") or "").strip().lower()
        import_run = (data.get("import_tomogram_run") or "").strip()
        downsample_vox = (data.get("downsample_tomogram_voxel_size") or "").strip()

        user_id = (data.get("user_id") or "").strip()
        encoded_password = data.get("password") or ""
        decoded_password = base64.b64decode(encoded_password).decode("utf-8") if encoded_password else ""

        # Basic validation
        missing = [
            k
            for k, v in {
                "user_id": user_id,
                "password": encoded_password,
                "session_name": session_name,
                "copick_run": copick_run,
                "import_tomo_type": import_type,
                "import_tomogram_run": import_run,
            }.items()
            if not v
        ]
        if missing:
            return JsonResponse({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        # Normalize run label: ensure "run###"
        if not copick_run.lower().startswith("run"):
            digits = "".join(ch for ch in copick_run if ch.isdigit())
            copick_run = f"run{digits.zfill(3)}" if digits else "run001"

        # Persist minimal auth (if you need later)
        request.session["user_id"] = user_id
        request.session["decoded_password"] = decoded_password

        # Sanitize copy for log (drop password)
        data_sanitized = dict(data)
        data_sanitized.pop("password", None)

        # -------- submit ----------
        submitter = RemoteJobSubmitter(
            cluster_id="bruno",
            auth={"username": user_id, "password": decoded_password},
            remote_script_dir=COPICK_SCRIPT_DIR,
        )
        submitter.connect()

        job_name = f"{session_name}_import_copick_{copick_run}"

        # Jinja keys must match your template placeholders
        out, err = submitter.run_script(
            template_path=COPICK_IMPORT_TOMO_TEMPLATE_PATH,
            job_name=job_name,
            session=session_name,
            copickRun=copick_run,
            importTomoType=import_type,
            importTomogramRun=import_run,
            downsampleTomogramVoxelSize=downsample_vox,
        )

        # Parse Slurm job id(s)
        ids = re.findall(r"Submitted batch job (\d+)", out or "")
        job_id_str = ",".join(ids) if ids else None

        store_log(
            job_name="CopickImport",
            request=request,
            data_sanitized=data_sanitized,
            error="",
            advanced_status=True,
            job_id=job_id_str,
        )

        return JsonResponse(
            {
                "message": f"Session {session_name}: copick import submitted.",
                "output": out,
                "error": err,
                "job_id": job_id_str,
            },
        )

    except Exception as e:
        store_log(
            job_name="CopickImport",
            request=request,
            data_sanitized=data_sanitized if "data_sanitized" in locals() else {},
            error=str(e),
            advanced_status=False,
            job_id=None,
        )
        return JsonResponse({"error": f"{e}: 500"}, status=500)
    finally:
        if "submitter" in locals():
            submitter.close()


@extend_schema(
    methods=["GET"],
    summary="List available template maps",
    description=(
        "Returns the available **template maps** by reading a local JSON file (or a remote fallback via SSH_connect_bruno). "
        "Use the optional `q` query to filter by name, relative path, or PDB ID (case-insensitive substring)."
    ),
    parameters=[
        OpenApiParameter(
            name="q",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional filter; matches against name, modelLocation, or pdbID (e.g. `?q=actin`)",
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="OK",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "basePath": "/hpc/projects/.../model_templates/",
                        "templates": [
                            {
                                "name": "actin",
                                "label": "actin — models/actin_12A.mrc",
                                "modelLocation": "models/actin_12A.mrc",
                                "absolutePath": "/hpc/projects/.../model_templates/models/actin_12A.mrc",
                                "voxelSize": 12,
                                "diameter": 70,
                                "symmetry": "C1",
                                "pdbID": "1J6Z",
                            },
                            {
                                "name": "ribosome",
                                "label": "ribosome — models/ribo_10A.mrc",
                                "modelLocation": "models/ribo_10A.mrc",
                                "absolutePath": "/hpc/projects/.../model_templates/models/ribo_10A.mrc",
                                "voxelSize": 10,
                                "diameter": 220,
                                "symmetry": "C1",
                                "pdbID": "4V6X",
                            },
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Template JSON not found locally or remotely",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Not Found",
                    value={"error": "Template JSON not found at /hpc/projects/.../template_params.json"},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Invalid JSON or unexpected server error",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Invalid JSON",
                    value={"error": "Invalid JSON: Expecting value: line 1 column 1 (char 0)"},
                    response_only=True,
                ),
                OpenApiExample(
                    "Server error",
                    value={"error": "Unexpected error in get_template_map_json: <details>"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["workflow"],
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_template_map_json(request):
    """Return list of available template maps."""

    # Configurable path
    local_path = getattr(
        settings,
        "PYTOM_TEMPLATE_PARAMS_PATH",
        "/hpc/projects/group.czii/krios1.processing/pytom/scripts/model_templates/template_params.json",
    )

    # Optional remote fallback path (same path on Bruno)
    remote_path = "/hpc/projects/group.czii/krios1.processing/pytom/scripts/model_templates/template_params.json"

    # Optional query filter
    q = (request.GET.get("q") or "").strip().lower()

    try:
        # Try local first
        if os.path.exists(local_path):
            logger.info(f"[get_template_map_json] Reading local JSON: {local_path}")
            with open(local_path, "r") as fh:
                raw_data = fh.read()
        else:
            # Fallback to remote SSH fetch
            logger.info(f"[get_template_map_json] Local file not found, fetching via SSH: {remote_path}")
            # pytom model templates live on bruno; read from there regardless of which cluster
            # other jobs ran on. `local_path` is the NFS mount served directly when available.
            raw_data = clusterio.read_remote_file("bruno", remote_path)

        # Parse JSON using your helper
        full_data = jsonify(raw_data)

        base_path = full_data.get("templateFolderPath", "")
        proteins = full_data.get("proteins", {})

        templates = []
        for name, meta in proteins.items():
            loc = meta.get("modelLocation", "")
            absolute = loc if os.path.isabs(loc) else os.path.join(base_path, loc)
            item = {
                "name": name,
                "label": f"{name} — {loc}",
                "modelLocation": loc,
                "absolutePath": absolute,
                "voxelSize": meta.get("modelVoxelSize"),
                "diameter": meta.get("modelDiameter"),
                "symmetry": meta.get("symmetry"),
                "pdbID": meta.get("pdbID"),
            }

            # optional filtering (?q=)
            if q:
                hay = " ".join(
                    [
                        name.lower(),
                        str(loc).lower(),
                        str(meta.get("pdbID") or "").lower(),
                    ],
                )
                if q not in hay:
                    continue

            templates.append(item)

        templates.sort(key=lambda x: x["name"].lower())
        return JsonResponse({"basePath": base_path, "templates": templates}, status=200)

    except FileNotFoundError:
        err = f"Template JSON not found locally or remotely at {local_path}"
        logger.error(err)
        return JsonResponse({"error": err}, status=404)
    except ValueError as ve:
        logger.exception(f"Invalid JSON content: {ve}")
        return JsonResponse({"error": f"Invalid JSON: {ve}"}, status=500)
    except clusterio.SSHDisabledError:
        # No cluster access (e.g. demo server) — degrade to an empty template list.
        return JsonResponse({"basePath": "", "templates": []}, status=200)
    except Exception as e:
        logger.exception(f"Unexpected error in get_template_map_json: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["POST"],
    summary="Add object to a CoPick procrun",
    description=(
        "Submits a remote Slurm job to add a new object to an existing CoPick processing run. "
        "Requires POST JSON body with authentication, session/run identifiers, and object name/diameter. "
        "Optional fields include PDB ID, object map file path, and map voxel size. "
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                # Authentication
                "user_id": {"type": "string", "example": "yyu"},
                "password": {
                    "type": "string",
                    "description": "Base64-encoded password",
                    "example": "c2VjcmV0MTIz",
                },
                # Required job info
                "session": {"type": "string", "example": "25sep18a"},
                "copick_procrun": {"type": "string", "example": "run002"},
                "object_name": {"type": "string", "example": "actin"},
                "object_diameter": {"type": "number", "example": 70},
                # Optional fields
                "pdb_id": {"type": "string", "nullable": True, "example": "1J6Z"},
                "object_map_file": {
                    "type": "string",
                    "nullable": True,
                    "description": "Absolute or relative path to an object map file",
                    "example": "/hpc/projects/.../models/actin_12A.mrc",
                },
                "object_voxel_size": {
                    "type": "number",
                    "nullable": True,
                    "example": 12.0,
                    "description": "Voxel size (must be numeric if provided)",
                },
            },
            "required": [
                "user_id",
                "password",
                "session",
                "copick_procrun",
                "object_name",
                "object_diameter",
            ],
        },
    },
    responses={
        200: OpenApiResponse(
            description="Job submitted successfully",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "message": "Add-object submitted for 25sep18a/run002",
                        "output": "Submitted batch job 456789\n",
                        "error": "",
                        "job_id": "456789",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad request (missing or invalid fields)",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Missing fields",
                    value={"error": "Missing fields: user_id, session"},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Unhandled server or remote submission error",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    "Server error",
                    value={"error": "Some traceback or connection error: 500"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["workflow"],
)
@csrf_exempt
@api_view(["POST"])
@login_required
def run_copick_add_object(request):
    """Add object to Copick processing run."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = request.data  # json.loads(request.body or "{}")

        user_id = (data.get("user_id") or "").strip()
        b64_pass = (data.get("password") or "").strip()
        password = base64.b64decode(b64_pass).decode("utf-8") if b64_pass else ""

        # Required
        session_name = (data.get("session") or "").strip()
        copick_procrun = (data.get("copick_procrun") or "").strip()
        object_name = (data.get("object_name") or "").strip()
        object_diam = (data.get("object_diameter") or "").strip()

        # Optional
        pdb_id = (data.get("pdb_id") or "").strip()
        object_map_file = (data.get("object_map_file") or "").strip()  # absolute path OK
        object_voxel_size = (data.get("object_voxel_size") or "").strip()  # must be numeric if provided

        missing = [
            k
            for k, v in {
                "user_id": user_id,
                "password": b64_pass,
                "session": session_name,
                "copick_procrun": copick_procrun,
                "object_name": object_name,
                "object_diameter": object_diam,
            }.items()
            if not v
        ]
        if missing:
            return JsonResponse({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        # Normalize run ("run###")
        if not copick_procrun.lower().startswith("run"):
            digits = "".join(ch for ch in copick_procrun if ch.isdigit())
            copick_procrun = f"run{digits.zfill(3)}" if digits else "run001"

        # Validate numeric diameter (and optional voxel)
        try:
            _ = float(object_diam)
        except ValueError:
            return JsonResponse({"error": "object_diameter must be numeric"}, status=400)
        if object_voxel_size and not re.fullmatch(r"\d+(\.\d+)?", object_voxel_size):
            return JsonResponse({"error": "object_voxel_size must be numeric when provided"}, status=400)

        # Submit job
        submitter = RemoteJobSubmitter(
            cluster_id="bruno",
            auth={"username": user_id, "password": password},
            remote_script_dir=COPICK_SCRIPT_DIR,
        )
        submitter.connect()
        job_name = f"{session_name}_add_object_{copick_procrun}"

        out, err = submitter.run_script(
            template_path=COPICK_ADD_OBJECT_TEMPLATE_PATH,
            job_name=job_name,
            session=session_name,
            copickRun=copick_procrun,
            objectName=object_name,
            objectDiameter=str(object_diam),
            pdbID=pdb_id,
            objectMapFile=object_map_file,
            objectVoxelSize=str(object_voxel_size) if object_voxel_size else "",
        )

        ids = re.findall(r"Submitted batch job (\d+)", out or "")
        job_id_str = ",".join(ids) if ids else None

        return JsonResponse(
            {
                "message": f"Add-object submitted for {session_name}/{copick_procrun}",
                "output": out,
                "error": err,
                "job_id": job_id_str,
            },
        )
    except Exception as e:
        return JsonResponse({"error": f"{e}: 500"}, status=500)
    finally:
        if "submitter" in locals():
            submitter.close()
