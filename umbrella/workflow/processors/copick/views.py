"""
Custom API views for Copick processor.

Provides processor-specific endpoints for:
- Dynamic form field options (available tomogram runs, operations)
- Custom parameter validation (check tomogram availability, project existence)
- Session-specific defaults (recommended voxel size based on pixel size)
- Processor metadata (Copick format info, examples)
"""

import json
import os

from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from processes.models import PipeExecution, ProcPlan, ProcRun
from processes.services.cluster_resolver import cluster_id_for_run
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from stores.models import Cluster, resolve_review_path
from tem.models import MsiSession

from .processor import CopickProcessor

COPICK_PLAN_NAME = "czii-copick"
COPICK_DEFAULT_CLUSTER_ID = CopickProcessor.cluster


@require_http_methods(["GET"])
def get_dynamic_options(request, session_id: str = None) -> JsonResponse:
    """
    Get dynamic dropdown options for Copick form fields.

    Args:
        request: Django HTTP request
        session_id: Optional MSI session ID (passed by generic processor options router)

    Query Parameters:
        session_id: Optional MSI session ID for session-specific options (fallback)

    Returns:
        JsonResponse with field options:
        {
            "tomogram_runs": [
                {"value": "run001", "label": "run001 - AreTomo3 (dctf)", "description": "..."},
                {"value": "run002", "label": "run002 - DenoisET (denoise)", "description": "..."},
                ...
            ],
            "operations": [
                {"value": "create", "label": "Create New Project", "description": "..."},
                {"value": "import", "label": "Import to Existing", "description": "..."}
            ]
        }
    """
    # Get session_id from parameter or query string
    if not session_id:
        session_id = request.GET.get("session_id")

    options = {
        "operation": [
            {
                "value": "create",
                "label": "Create New Copick Project",
                "description": "Initialize a new Copick project and import tomograms",
            },
            {
                "value": "add_object",
                "label": "Add Pickable Object",
                "description": "Add a pickable object definition to an existing Copick project",
            },
            {
                "value": "import_tomograms",
                "label": "Import Tomograms",
                "description": "Import tomograms to an existing Copick project",
            },
        ],
        "import_tomo_type": [
            {
                "value": "dctf",
                "label": "DCTF",
                "description": "Dose-compensated reconstruction from AreTomo3",
            },
            {
                "value": "sart",
                "label": "SART",
                "description": "SART reconstruction from AreTomo3",
            },
            {
                "value": "wbp",
                "label": "WBP",
                "description": "Standard reconstruction without dose compensation",
            },
            {
                "value": "denoise",
                "label": "Denoised",
                "description": "DenoisET-processed tomograms",
            },
        ],
    }

    # Get available tomogram runs for the session
    if session_id:
        try:
            session = MsiSession.objects.get(name=session_id)

            # Get AreTomo3 and DenoisET runs for the session
            # Use the same plan mapping as the legacy implementation
            from processes.models import ProcPlan

            # Get the selected tomogram type to filter runs
            # If "denoise" → only show DenoisET runs
            # If "dctf", "sart", or "wbp" → only show AreTomo3 runs
            # If not provided → show both (backward compatibility)
            import_tomo_type = request.GET.get("import_tomo_type", "").lower()

            options["import_tomogram_run"] = []

            # Get AreTomo3 runs (for dctf, sart, wbp types)
            if not import_tomo_type or import_tomo_type in ["dctf", "sart", "wbp"]:
                try:
                    aretomo_plan = ProcPlan.objects.get(name="czii-live")
                    aretomo_runs = ProcRun.objects.filter(msi_session=session, proc_plan=aretomo_plan).order_by(
                        "-created_at"
                    )

                    for run in aretomo_runs:
                        # Label includes the type for clarity
                        tomo_type_label = import_tomo_type.upper() if import_tomo_type else "DCTF/SART/WBP"
                        options["import_tomogram_run"].append(
                            {
                                "value": run.name,
                                "label": f"{run.name} (AreTomo3)",
                                "description": f"{tomo_type_label} reconstruction - Created {run.created_at.strftime('%Y-%m-%d %H:%M')}",
                            }
                        )
                except ProcPlan.DoesNotExist:
                    pass

            # Get DenoisET runs (for denoise type)
            if not import_tomo_type or import_tomo_type == "denoise":
                try:
                    denoise_plan = ProcPlan.objects.get(name="czii-denoise")
                    denoise_runs = ProcRun.objects.filter(msi_session=session, proc_plan=denoise_plan).order_by(
                        "-created_at"
                    )

                    for run in denoise_runs:
                        options["import_tomogram_run"].append(
                            {
                                "value": run.name,
                                "label": f"{run.name} (DenoisET)",
                                "description": f"Denoised tomograms - Created {run.created_at.strftime('%Y-%m-%d %H:%M')}",
                            }
                        )
                except ProcPlan.DoesNotExist:
                    pass

            if not options["import_tomogram_run"]:
                options["import_tomogram_run"] = [
                    {
                        "value": "",
                        "label": "No tomogram runs found for this session",
                        "description": "Please run AreTomo3 or DenoisET first",
                    }
                ]

        except MsiSession.DoesNotExist:
            options["import_tomogram_run"] = []

    # Add copick_session options (for add_object and import_tomograms operations)
    # Always show sessions that have existing Copick ProcRuns
    # (needed when user switches from Create mode to Import mode)
    try:
        from processes.models import ProcPlan

        copick_plan = ProcPlan.objects.get(name="czii-copick")

        # Get unique sessions that have Copick runs
        sessions_with_copick = MsiSession.objects.filter(procrun__proc_plan=copick_plan).distinct().order_by("-name")

        options["copick_session"] = [
            {
                "value": session.name,
                "label": session.name,
                "description": "Session with Copick project",
            }
            for session in sessions_with_copick
        ]

    except ProcPlan.DoesNotExist:
        options["copick_session"] = []

    # Add template maps (loaded from get_template_maps endpoint)
    # Note: Frontend will call get_template_maps separately for full metadata

    template_maps_dir = "/hpc/projects/group.czii/krios1.processing/copick/template_maps"
    options["template_map_name"] = []
    try:
        if os.path.exists(template_maps_dir):
            for filename in os.listdir(template_maps_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(template_maps_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            map_data = json.load(f)
                            options["template_map_name"].append(
                                {
                                    "value": map_data.get("name", filename.replace(".json", "")),
                                    "label": map_data.get("label", map_data.get("name", filename)),
                                    "description": f"{map_data.get('diameter', 0)}Å, PDB: {map_data.get('pdb_id', 'N/A')}",
                                }
                            )
                    except (json.JSONDecodeError, IOError):
                        continue
            options["template_map_name"].sort(key=lambda x: x["label"])
    except Exception:
        pass

    # Add copick_run options (for add_object operation)
    # Shows run names for the selected copick_session
    copick_session_param = request.GET.get("copick_session")
    if copick_session_param:
        try:
            from processes.models import ProcPlan

            copick_plan = ProcPlan.objects.get(name="czii-copick")
            session_obj = MsiSession.objects.get(name=copick_session_param)

            # Get runs for this session under the Copick plan
            copick_runs = ProcRun.objects.filter(proc_plan=copick_plan, msi_session=session_obj).order_by("-created_at")

            options["copick_run"] = [
                {
                    "value": run.name,
                    "label": run.name,
                    "description": f"Created {run.created_at.strftime('%Y-%m-%d %H:%M')}",
                }
                for run in copick_runs
            ]

        except (ProcPlan.DoesNotExist, MsiSession.DoesNotExist):
            options["copick_run"] = []

    return JsonResponse(
        {
            "success": True,
            "options": options,
        }
    )


@require_http_methods(["POST"])
def validate_parameters(request) -> JsonResponse:
    """
    Validate Copick parameters before submission.

    Performs custom validation:
    - Check that specified tomogram run exists
    - Verify tomogram type matches the run's processor
    - For import operation, check that Copick project exists
    - Validate voxel size is appropriate

    Args:
        request: Django HTTP request with JSON body containing parameters

    Returns:
        JsonResponse with validation results
    """

    try:
        params = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "valid": False,
                "errors": [{"field": "__all__", "message": "Invalid JSON in request body"}],
            }
        )

    errors = []

    # Validate operation
    operation = params.get("operation", "create")
    if operation not in ["create", "add_object", "import_tomograms"]:
        errors.append(
            {
                "field": "operation",
                "message": 'Operation must be "create", "add_object", or "import_tomograms"',
            }
        )
        return JsonResponse(
            {
                "valid": False,
                "errors": errors,
            }
        )

    # Validate import_tomograms mode parameters
    if operation == "import_tomograms":
        if not params.get("copick_session"):
            errors.append(
                {
                    "field": "copick_session",
                    "message": "Copick session is required for import_tomograms operation",
                }
            )

        if not params.get("copick_run"):
            errors.append(
                {
                    "field": "copick_run",
                    "message": "Copick run is required for import_tomograms operation",
                }
            )

        import_tomogram_run = params.get("import_tomogram_run")
        if not import_tomogram_run:
            errors.append(
                {
                    "field": "import_tomogram_run",
                    "message": "Tomogram run number is required for import_tomograms operation",
                }
            )

        import_tomo_type = params.get("import_tomo_type")
        valid_types = ["dctf", "wbp", "denoise", "sart"]
        if import_tomo_type and import_tomo_type not in valid_types:
            errors.append(
                {
                    "field": "import_tomo_type",
                    "message": f"Invalid tomogram type. Must be one of: {', '.join(valid_types)}",
                }
            )

        downsample_voxel_size = params.get("downsample_voxel_size")
        if downsample_voxel_size is not None:
            try:
                voxel_size = float(downsample_voxel_size)
                if voxel_size < 1.0 or voxel_size > 100.0:
                    errors.append(
                        {
                            "field": "downsample_voxel_size",
                            "message": "Voxel size must be between 1.0 and 100.0 Angstroms",
                        }
                    )
            except (ValueError, TypeError):
                errors.append(
                    {
                        "field": "downsample_voxel_size",
                        "message": "Voxel size must be a valid number",
                    }
                )

    # Validate add_object mode parameters
    if operation == "add_object":
        required_fields = ["copick_session", "copick_run", "object_name", "object_diameter"]
        for field in required_fields:
            if not params.get(field):
                errors.append(
                    {
                        "field": field,
                        "message": f"{field} is required for add_object operation",
                    }
                )

        # Validate that either template_map_name or object_map_file is provided
        if not params.get("template_map_name") and not params.get("object_map_file"):
            errors.append(
                {
                    "field": "template_map_name",
                    "message": "Either template_map_name or object_map_file must be provided",
                }
            )

        # If object_map_file is provided, object_voxel_size is required
        if params.get("object_map_file") and not params.get("object_voxel_size"):
            errors.append(
                {
                    "field": "object_voxel_size",
                    "message": "object_voxel_size is required when object_map_file is provided",
                }
            )

    return JsonResponse(
        {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    )


@require_http_methods(["GET"])
def get_session_defaults(request, session_id: str = None) -> JsonResponse:
    """
    Get recommended default parameters for Copick export.

    Suggests parameters based on session characteristics:
    - Voxel size based on pixel size and typical downsampling
    - Operation type based on existing Copick projects
    - Tomogram type based on available runs

    Args:
        request: Django HTTP request
        session_id: MSI session ID

    Returns:
        JsonResponse with default parameter values
    """
    defaults = {
        "operation": "create",
        "import_tomo_type": "dctf",
    }

    if session_id:
        try:
            session = MsiSession.objects.get(name=session_id)

            # TODO: Calculate recommended voxel size based on pixel size
            # For example, if pixel size is 2.5Å, suggest 10Å (4x binning)
            defaults["downsample_voxel_size"] = 10.0

            # TODO: Check if Copick project already exists for this session
            # If so, default to 'import' operation
            # For now, default to 'create'
            defaults["operation"] = "create"

        except MsiSession.DoesNotExist:
            pass

    return JsonResponse(
        {
            "success": True,
            "defaults": defaults,
        }
    )


@require_http_methods(["GET"])
def get_processor_metadata(request) -> JsonResponse:
    """
    Get Copick processor metadata for UI display.

    Returns help text, format information, and documentation links.

    Args:
        request: Django HTTP request

    Returns:
        JsonResponse with processor metadata
    """
    return JsonResponse(
        {
            "success": True,
            "metadata": {
                "help_text": (
                    "Copick provides three operations for managing cryoET projects: "
                    "(1) Create new Copick projects with tomograms, "
                    "(2) Add pickable object definitions for particle picking, "
                    "(3) Import additional tomograms to existing projects. "
                    "Copick uses a standardized data structure that enables downstream analysis "
                    "with Copick-compatible tools and facilitates data sharing."
                ),
                "category": "Export & Annotation",
                "examples": [
                    {
                        "title": "Create new Copick project with DCTF tomograms",
                        "description": "Initialize a new Copick project and import dose-compensated tomograms from AreTomo3",
                        "params": {
                            "operation": "create",
                            "import_tomogram_run": "run001",
                            "import_tomo_type": "dctf",
                            "downsample_voxel_size": 10.0,
                        },
                    },
                    {
                        "title": "Add ribosome object definition",
                        "description": "Add a pickable ribosome object using a template map from the database",
                        "params": {
                            "operation": "add_object",
                            "copick_session": "24nov10",
                            "copick_run": "TS_001",
                            "object_name": "ribosome",
                            "object_diameter": 300.0,
                            "template_map_name": "ribosome_4v6x",
                            "pdb_id": "4V6X",
                        },
                    },
                    {
                        "title": "Add custom object with user-provided map",
                        "description": "Add a pickable object using a custom MRC/MAP file",
                        "params": {
                            "operation": "add_object",
                            "copick_session": "24nov10",
                            "copick_run": "TS_001",
                            "object_name": "membrane_protein",
                            "object_diameter": 120.0,
                            "object_map_file": "/path/to/custom_protein.mrc",
                            "object_voxel_size": 2.5,
                        },
                    },
                    {
                        "title": "Import denoised tomograms to existing project",
                        "description": "Add DenoisET-processed tomograms to an existing Copick project",
                        "params": {
                            "operation": "import_tomograms",
                            "copick_session": "24nov10",
                            "copick_run": "TS_001",
                            "import_tomogram_run": "run002",
                            "import_tomo_type": "denoise",
                            "downsample_voxel_size": 10.0,
                        },
                    },
                ],
                "docs_url": "https://github.com/czimaginginstitute/copick",
                "parameter_notes": {
                    "operation": (
                        "Choose operation mode: "
                        "create (new project), "
                        "add_object (add pickable objects), "
                        "import_tomograms (add more tomograms)."
                    ),
                    "copick_session": "Select the Copick session to work with (for add_object and import_tomograms operations).",
                    "copick_run": "Select the Copick run within the session (for add_object and import_tomograms operations).",
                    "object_name": "Name of the pickable object (e.g., ribosome, membrane, vesicle).",
                    "object_diameter": "Diameter of the object in Angstroms. Used for particle picking.",
                    "template_map_name": "Select a pre-configured template map from the database.",
                    "object_map_file": "Path to custom MRC/MAP file. Overrides template_map_name if provided.",
                    "object_voxel_size": "Voxel size of custom map file (required when using object_map_file).",
                    "pdb_id": "Optional Protein Data Bank ID (e.g., 4V6X) associated with the object.",
                    "import_tomogram_run": "Processing run containing tomograms (for create/import_tomograms).",
                    "import_tomo_type": "Tomogram type: dctf (dose-compensated), wbp (weighted back projection), or denoise (denoised).",
                    "downsample_voxel_size": "Optional. Downsample tomograms to this voxel size (Angstroms). Leave empty to keep original resolution.",
                },
                "output_format": {
                    "structure": "Copick project directory with standardized layout",
                    "files": [
                        "config.json - Copick project configuration",
                        "ExperimentRuns/ - Copick run directories",
                        "static/ - Template maps and objects",
                        "picks/ - Particle picks in Zarr format",
                        "meshes/ - Mesh annotations in GLB format",
                    ],
                    "compatible_tools": [
                        "napari-copick",
                        "copick-cli",
                        "cryoET data portal",
                        "custom analysis scripts",
                    ],
                },
            },
        }
    )


@require_http_methods(["GET"])
def get_template_maps(request) -> JsonResponse:
    """
    Get available template maps for Copick objects.

    Reads template map metadata from JSON files in the template_maps directory.
    Each template map includes information about the map file, diameter, and PDB ID.

    Args:
        request: Django HTTP request

    Returns:
        JsonResponse with template maps:
        {
            "success": True,
            "template_maps": [
                {
                    "name": "ribosome_4v6x",
                    "label": "Ribosome (4V6X)",
                    "diameter": 300.0,
                    "pdb_id": "4V6X",
                    "map_file": "/path/to/ribosome.mrc",
                    "voxel_size": 2.5,
                    "description": "80S ribosome structure"
                },
                ...
            ]
        }
    """

    template_maps = []

    # Path to template maps metadata directory
    template_maps_dir = "/hpc/projects/group.czii/krios1.processing/copick/template_maps"

    try:
        if os.path.exists(template_maps_dir):
            # Read all JSON files in the template maps directory
            for filename in os.listdir(template_maps_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(template_maps_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            map_data = json.load(f)
                            template_maps.append(
                                {
                                    "name": map_data.get("name", filename.replace(".json", "")),
                                    "label": map_data.get("label", map_data.get("name", filename)),
                                    "diameter": map_data.get("diameter", 0),
                                    "pdb_id": map_data.get("pdb_id", ""),
                                    "map_file": map_data.get("map_file", ""),
                                    "voxel_size": map_data.get("voxel_size", 0),
                                    "description": map_data.get("description", ""),
                                }
                            )
                    except (json.JSONDecodeError, IOError) as e:
                        # Skip invalid JSON files
                        continue

        # Sort by label for easier browsing
        template_maps.sort(key=lambda x: x["label"])

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"Failed to load template maps: {str(e)}",
                "template_maps": [],
            }
        )

    return JsonResponse(
        {
            "success": True,
            "template_maps": template_maps,
        }
    )


@require_http_methods(["GET"])
def get_copick_runs(request) -> JsonResponse:
    """
    Get available Copick runs for a given session.

    Lists the ProcRuns under the czii-copick plan for the session - a DB query, so no HPC mount.
    `description` is the run's copick config.json path on the cluster.

    Args:
        request: Django HTTP request with a ?session_id= query parameter

    Returns:
        JsonResponse with Copick runs:
        {
            "success": True,
            "copick_runs": [
                {
                    "name": "run001",
                    "label": "run001",
                    "description": "/hpc/projects/group.czii/krios1.processing/copick/<session>/run001/config.json"
                },
                ...
            ]
        }
    """
    # Extract session_id from query parameters
    session_id = request.GET.get("session_id")

    if not session_id:
        return JsonResponse(
            {
                "success": False,
                "error": "session_id is required",
                "copick_runs": [],
            }
        )

    try:
        plan = ProcPlan.objects.get(name=COPICK_PLAN_NAME)
        session_obj = MsiSession.objects.get(name=session_id)
    except (ProcPlan.DoesNotExist, MsiSession.DoesNotExist):
        return JsonResponse(
            {
                "success": True,
                "copick_runs": [],
                "message": "No Copick runs found for this session. Create a Copick project first.",
            }
        )

    runs = ProcRun.objects.filter(proc_plan=plan, msi_session=session_obj).order_by("-created_at")
    copick_runs = [
        {
            "name": run.name,
            "label": run.name,
            "description": f"/hpc/projects/group.czii/krios1.processing/copick/{session_id}/{run.name}/config.json",
        }
        for run in runs
    ]

    return JsonResponse({"success": True, "copick_runs": copick_runs})


def _latest_pipe_status(proc_run) -> str:
    latest = (
        PipeExecution.objects.filter(proc_run=proc_run).order_by("-updated_at").values_list("status", flat=True).first()
    )
    return latest or "pending"


def _build_copick_project(proc_run) -> dict:
    session = proc_run.msi_session
    cluster_id = cluster_id_for_run(session.name, proc_run.name, default=COPICK_DEFAULT_CLUSTER_ID)
    cluster = Cluster.objects.get(cluster_id=cluster_id)
    root_url = resolve_review_path(
        "copick_url",
        cluster=cluster,
        msi_session=session,
        copick_run=proc_run.name,
    )
    # TODO: eventually symlink of data folders to save space, so data_url may change.
    return {
        "session_name": session.name,
        "run_name": proc_run.name,
        "cluster_id": cluster_id,
        "scope": session.session_plan.scope.name.lower(),
        "root_url": root_url,
        "config_url": root_url + "config.json",
        "data_url": root_url,
        "status": _latest_pipe_status(proc_run),
        "created_at": proc_run.created_at.isoformat(),
        "proc_run_id": proc_run.id,
    }


@extend_schema(
    methods=["GET"],
    tags=["Copick Projects"],
    description=(
        "List copick projects (one row per ProcRun under the czii-copick plan). "
        "Each entry includes the HTTP URL of the project root so the copick viewer "
        "can fetch config.json and the overlay data directly."
    ),
    parameters=[
        OpenApiParameter(
            name="cluster",
            required=False,
            type={"type": "array", "items": {"type": "string"}},
            description=(
                "Filter by one or more cluster ids (e.g. 'czii', 'bruno'). "
                "Repeat the param (?cluster=czii&cluster=bruno) or pass a comma-separated "
                "list (?cluster=czii,bruno). Omit to include all clusters."
            ),
        ),
        OpenApiParameter(
            name="session_id",
            required=False,
            type=OpenApiTypes.STR,
            description="Filter to a single MsiSession.name.",
        ),
        OpenApiParameter(
            name="status",
            required=False,
            type=OpenApiTypes.STR,
            description="'completed' (default) returns only runs with a completed PipeExecution. 'all' returns every run.",
        ),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
@login_not_required
@api_view(["GET"])
@permission_classes([AllowAny])
@require_http_methods(["GET"])
def list_copick_projects(request) -> JsonResponse:
    """List copick projects (one row per ProcRun under the czii-copick plan).

    Query params:
        cluster: filter by one or more cluster ids (e.g. 'czii', 'bruno').
            Repeat the param or pass a comma-separated list. Omit for all clusters.
        session_id: filter to a single MsiSession.name
        status: 'completed' (default) or 'all'
    """
    try:
        plan = ProcPlan.objects.get(name=COPICK_PLAN_NAME)
    except ProcPlan.DoesNotExist:
        return JsonResponse({"success": True, "projects": []})

    qs = ProcRun.objects.filter(proc_plan=plan).select_related("msi_session__session_plan__scope")

    session_id = request.GET.get("session_id")
    if session_id:
        qs = qs.filter(msi_session__name=session_id)

    status_filter = request.GET.get("status", "completed")
    if status_filter == "completed":
        qs = qs.filter(pipe_executions__status="completed").distinct()

    qs = qs.order_by("-created_at")

    projects = [_build_copick_project(r) for r in qs]

    cluster_filters = {c.strip() for raw in request.GET.getlist("cluster") for c in raw.split(",") if c.strip()}
    if cluster_filters:
        projects = [p for p in projects if p["cluster_id"] in cluster_filters]

    return JsonResponse({"success": True, "projects": projects})


@extend_schema(
    methods=["GET"],
    tags=["Copick Projects"],
    description=(
        "Return a copick project. Pass ?scan=true to include picks/segs/meshes from the cluster (SSH, slower)."
    ),
    parameters=[
        OpenApiParameter(
            name="scan",
            required=False,
            type=OpenApiTypes.BOOL,
            description="If true, include scanned picks/segmentations/meshes under `annotations`.",
        ),
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@login_not_required
@api_view(["GET"])
@permission_classes([AllowAny])
@require_http_methods(["GET"])
def get_copick_project_detail(request, session_name: str, run_name: str) -> JsonResponse:
    """Return a single copick project by (session_name, run_name)."""
    try:
        run = ProcRun.objects.select_related("msi_session__session_plan__scope").get(
            proc_plan__name=COPICK_PLAN_NAME,
            msi_session__name=session_name,
            name=run_name,
        )
    except ProcRun.DoesNotExist:
        return JsonResponse({"success": False, "error": "Copick project not found"}, status=404)

    project = _build_copick_project(run)

    if request.GET.get("scan", "").lower() in ("1", "true", "yes"):
        from .scan import COPICK_CONFIG_PATH, scan_copick_project

        config_path = COPICK_CONFIG_PATH.format(session=session_name, run=run_name)
        project["annotations"] = scan_copick_project(project["cluster_id"], config_path)

    return JsonResponse({"success": True, "project": project})
