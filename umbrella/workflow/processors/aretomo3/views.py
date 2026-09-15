"""
Custom API views for AreTomo3 processor.

Provides processor-specific endpoints for:
- Dynamic form field options (gain files, previous runs)
- Session info shown beside the form (user, magnification, project, grid)
- Processor metadata (help text, examples, documentation)
"""

from typing import Any, Dict, List, Optional

from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from processes.services.cluster_resolver import get_default_cluster_id
from tem.models import GAIN_ROLE, CalibratedPixelSize, Magnification, MsiSession
from umbrella_logger import logger

from workflow.processors.aretomo3 import gain_file_fetcher, mdoc_reader
from workflow.processors.aretomo3.processor import NO_DIRECTORY


def _request_cluster_id(request) -> str:
    """The cluster the form is targeting, else the configured default."""
    return request.GET.get("cluster_id") or get_default_cluster_id()


def get_gain_file_options(session: MsiSession, cluster_id: str) -> List[Dict[str, str]]:
    """
    Get gain files formatted as dropdown options for the frontend.

    The directory and filename convention come from the session's camera (or a plan
    binding); files are sorted newest first. Empty when no gain directory resolves.

    Args:
        session: The MSI session the job is for
        cluster_id: Cluster to connect to

    Returns:
        List of option dicts for frontend dropdown:
        [
            {'value': '20251218_093959_EER_GainReference.gain', 'label': '... (most recent)', 'description': '...'},
            {'value': '20251201_080000_EER_GainReference.gain', 'label': '...', 'description': '...'},
            ...
        ]
    """
    options = []

    directory = session.get_session_dir(GAIN_ROLE)
    if directory == NO_DIRECTORY:
        logger.info(f"Session {session.name} resolves no gain directory; offering no gain options")
        return options

    pattern = session.get_file_pattern(GAIN_ROLE)
    result = gain_file_fetcher.list_gain_files(directory, cluster_id=cluster_id, file_pattern=pattern)
    if not result["success"]:
        logger.warning(f"Failed to fetch gain files: {result['error']}")
        return options

    for i, file_info in enumerate(result["files"]):
        label = file_info["filename"]
        if i == 0:
            label = f"{label} (most recent)"

        options.append(
            {
                "value": file_info["filename"],
                "label": label,
                "description": f"Modified: {file_info['modified_time']}",
            }
        )

    return options


@require_http_methods(["GET"])
def get_dynamic_options(request, session_id: str = None) -> JsonResponse:
    """
    Get dynamic dropdown options for AreTomo3 form fields.

    Args:
        request: Django HTTP request
        session_id: Optional MSI session ID for session-specific options

    Returns:
        JsonResponse with field options:
        {
            "gain_file_name": [
                {"value": "20251218_093959_EER_GainReference.gain", "label": "... (most recent)", "description": "..."},
                ...
            ]
        }
    """
    options = {"gain_file_name": []}

    # Gain lives where the session's camera says (Falcon4i: a shared folder; GatanCeltic: beside
    # the frames), so there is nothing to list without a session.
    session = MsiSession.objects.filter(name=session_id).first() if session_id else None
    if session is None:
        return JsonResponse({"success": True, "options": options})

    try:
        gain_options = get_gain_file_options(session, _request_cluster_id(request))
        options["gain_file_name"] = gain_options
        logger.info(f"Loaded {len(gain_options)} gain file options for AreTomo3")
    except Exception as e:
        logger.error(f"Error fetching gain files: {e}")

    return JsonResponse(
        {
            "success": True,
            "options": options,
        }
    )


def _suggest_pixel_size_for_mdoc_mag(mdoc_mag: int, session_plan) -> Optional[Dict[str, Any]]:
    """
    Given a magnification value from the MDOC, look up what the pixel size
    would be using the session's scope and camera.

    Searches Magnification records matching the scope and nominal_mag,
    then finds the latest CalibratedPixelSize for that mag + camera.

    Returns:
        {'pixel_size': float, 'nominal_mag': int} or None
    """
    mags = Magnification.objects.filter(
        scope=session_plan.scope,
        nominal_mag=mdoc_mag,
    )
    if not mags.exists():
        return None

    for mag in mags:
        cal = (
            CalibratedPixelSize.objects.filter(
                mag=mag,
                camera=session_plan.camera,
            )
            .order_by("-calibrated_at")
            .first()
        )
        if cal:
            return {
                "pixel_size": cal.pixel_spacing,
                "nominal_mag": mag.nominal_mag,
            }
    return None


def get_session_info(session: MsiSession) -> Dict[str, Any]:
    """
    Session metadata shown next to the launch form: user, magnification, project, grid.

    Parameter defaults are not decided here; see AreTomo3Processor.session_defaults
    and workflow.defaults.resolve_defaults.
    """
    session_info = {
        "user": session.user.username if session.user else None,
        "super_resolution": session.super_resolution,
    }

    # Add magnification info for transparency
    if session.magnification:
        session_info["magnification"] = {
            "nominal_mag": session.magnification.nominal_mag,
            "scope": session.magnification.scope.name,
            "pixel_size": session.get_calibrated_pixel_size(),
        }

    # Add project info if available
    if session.project:
        session_info["project"] = {
            "id": session.project.id,
            "name": session.project.name,
        }

    # Add grid info if available
    if session.grid:
        grid = session.grid
        session_info["grid"] = {
            "id": grid.id,
            "created": grid.create_on,
            "user": grid.user.username if grid.user else None,
            "specimen": grid.specimen.id if grid.specimen else None,
        }

        # Add freezing session info if available
        if grid.freezing_session:
            fs = grid.freezing_session
            session_info["grid"]["freezing_session"] = {
                "id": fs.id,
                "user": fs.user.username if fs.user else None,
                "datetime": fs.datetime,
                "documentation_page": model_to_dict(fs.documentation_page) if fs.documentation_page else None,
            }

    return session_info


@require_http_methods(["GET"])
def get_processor_metadata(request) -> JsonResponse:
    """
    Get AreTomo3 processor metadata for UI display.
    This is generic place to provide misc. data to the frontend for this processor

    Args:
        request: Django HTTP request

    Returns:
        JsonResponse with processor metadata:
        {
            "help_text": "AreTomo3 performs tomographic reconstruction...",
            "docs_url": "https://docs.example.com/aretomo3"
        }
    """
    return JsonResponse(
        {
            "success": True,
            "metadata": {
                "help_text": "AreTomo3 is awesome",
                "category": "Pre-processing",
                "docs_url": "https://github.com/czimaginginstitute/AreTomo3",
            },
        }
    )


@require_http_methods(["GET"])
def validate_session(request, session_id: str = None) -> JsonResponse:
    """
    Validate session data by cross-referencing MDOC magnification on cluster.

    This is separated from the defaults endpoint because the SSH round-trip
    to read the MDOC file is slow (~7s) and shouldn't block form loading.

    Args:
        request: Django HTTP request
        session_id: MSI session ID

    Returns:
        JsonResponse with validation results nested under magnification.pixel_size_validation
    """
    if not session_id:
        return JsonResponse({"success": True, "validation": {}})

    try:
        session = MsiSession.objects.get(name=session_id)
    except MsiSession.DoesNotExist:
        return JsonResponse({"success": True, "validation": {}})

    validation = {}
    try:
        # The session's own resolution is the directory -- no assembled path, no
        # assumed scope. "." means the plan's software emits no mdocs; skip quietly,
        # matching how any other read failure is treated below.
        mdocs_dir = session.get_session_dir("mdocs")
        if mdocs_dir == NO_DIRECTORY:
            return JsonResponse({"success": True, "validation": {}})
        pattern = session.get_file_pattern("mdocs")
        mdoc_result = mdoc_reader.read_mdoc_magnification(
            mdocs_dir,
            cluster_id=_request_cluster_id(request),
            list_glob=pattern.list_glob if pattern else mdoc_reader.DEFAULT_MDOC_GLOB,
        )
        if mdoc_result["success"]:
            mdoc_mag = mdoc_result["magnification"]
            validation["mdoc_magnification"] = mdoc_mag
            validation["mdoc_file"] = mdoc_result["mdoc_file"]

            if session.magnification:
                db_mag = session.magnification.nominal_mag
                if mdoc_mag != db_mag:
                    validation["mismatch"] = True
                    validation["warning"] = (
                        f"MDOC magnification ({mdoc_mag}) does not match "
                        f"session magnification ({db_mag}). "
                        f"The pixel size may be incorrect."
                    )
                    suggested = _suggest_pixel_size_for_mdoc_mag(mdoc_mag, session.session_plan)
                    if suggested:
                        validation["suggested_pixel_size"] = suggested["pixel_size"]
                        validation["suggested_magnification"] = suggested["nominal_mag"]
                else:
                    validation["mismatch"] = False
            else:
                validation["missing"] = True
                validation["warning"] = f"Session has no magnification set. MDOC reports {mdoc_mag}x."
                suggested = _suggest_pixel_size_for_mdoc_mag(mdoc_mag, session.session_plan)
                if suggested:
                    validation["suggested_pixel_size"] = suggested["pixel_size"]
                    validation["suggested_magnification"] = suggested["nominal_mag"]
        else:
            validation["error"] = mdoc_result["error"]
    except Exception as e:
        logger.warning(f"Failed to read MDOC magnification: {e}")
        validation["error"] = str(e)

    return JsonResponse({"success": True, "validation": validation})
