"""
Custom API views for AreTomo3 processor.

Provides processor-specific endpoints for:
- Dynamic form field options (gain files, previous runs)
- Session-specific defaults (pixel size, doses from TEM session)
- Processor metadata (help text, examples, documentation)
"""

from typing import Dict, List

from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from tem.models import MsiSession
from umbrella_logger import logger

from workflow.processors.aretomo3 import gain_file_fetcher


def get_gain_file_options(cluster_id: str = "czii") -> List[Dict[str, str]]:
    """
    Get gain files formatted as dropdown options for the frontend.

    Files are sorted by modification time (most recent first).

    Args:
        cluster_id: Cluster to connect to

    Returns:
        List of option dicts for frontend dropdown:
        [
            {'value': 'SuperRef_127684.mrc', 'label': 'SuperRef_127684.mrc (most recent)', 'description': '...'},
            {'value': 'SuperRef_127683.mrc', 'label': 'SuperRef_127683.mrc', 'description': '...'},
            ...
        ]
    """
    result = gain_file_fetcher.list_gain_files(cluster_id=cluster_id)

    options = []

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
                "description": f"Modified: {file_info['modified_time']} | Size: {file_info['size_human']}",
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
                {"value": "", "label": "Auto (most recent)", "description": "..."},
                {"value": "SuperRef_127684.mrc", "label": "SuperRef_127684.mrc", "description": "..."},
                ...
            ]
        }
    """
    options = {}

    # Fetch gain files from the cluster
    # Note: We always fetch gain files regardless of session_id since they're
    # stored in a shared location on the microscope
    try:
        gain_options = get_gain_file_options(cluster_id="czii")
        options["gain_file_name"] = gain_options
        logger.info(f"Loaded {len(gain_options)} gain file options for AreTomo3")
    except Exception as e:
        logger.error(f"Error fetching gain files: {e}")
        options["gain_file_name"] = []

    return JsonResponse(
        {
            "success": True,
            "options": options,
        }
    )


@require_http_methods(["GET"])
def get_session_defaults(request, session_id: str = None) -> JsonResponse:
    """
    Get recommended default parameters for a specific TEM session.

    Extracts session metadata to provide intelligent defaults:
    - Pixel size from microscope configuration
    - Total dose from session protocol
    - Frame dose calculated from typical frame count

    Args:
        request: Django HTTP request
        session_id: MSI session ID

    Returns:
        JsonResponse with default parameter values:
        {
            "defaults": {
                "pixel_size": 2.5,
                "align_z": 800,
                "vol_z": 1600
            }
        }
    """
    defaults = {}
    session_info = {}

    if session_id:
        try:
            session = MsiSession.objects.get(name=session_id)

            # Populate pixel_size from calibrated pixel size if available
            pixel_size = session.get_calibrated_pixel_size()
            if pixel_size is not None:
                defaults["pixel_size"] = pixel_size

            session_info = {
                "user": session.user.username if session.user else None,
            }

            # Add magnification info for transparency
            if session.magnification:
                session_info["magnification"] = {
                    "nominal_mag": session.magnification.nominal_mag,
                    "scope": session.magnification.scope.name,
                    "pixel_size": pixel_size,
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

        except MsiSession.DoesNotExist:
            pass

    return JsonResponse(
        {
            "success": True,
            "session_info": session_info,
            "defaults": defaults,
        }
    )


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
