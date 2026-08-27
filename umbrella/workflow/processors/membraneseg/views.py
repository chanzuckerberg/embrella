"""
Custom API views for Membrane Segmentation processor.

Provides processor-specific endpoints for:
- Dynamic form field options (copick sessions, runs, tomo types, voxel sizes)
- Cascading dropdown support via tomo-combos remote script
- Custom parameter validation
- Processor metadata
"""

import json
import re
from collections import defaultdict
from typing import Any, Dict

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from processes.models import ProcPlan, ProcRun
from tem.models import MsiSession
from umbrella_logger import logger

from common.clusterio import FIND_TYPE_DIR, find_paths


def _copick_root(cluster_id: str) -> str:
    """Copick's processing root -- from the same template the job scripts render with."""
    from workflow.processors import get_processor

    return get_processor("copick").get_processing_base_path(cluster=cluster_id)


def _get_tomo_combos(session: str, procrun: str, cluster_id: str = "bruno") -> Dict[str, Any]:
    """
    Get available tomogram type and voxel size combinations from the remote filesystem.

    Uses a single SSH `find` command to efficiently scan the Copick project directory
    structure, then parses the results in Python. This avoids many round-trip SFTP calls.

    Directory structure scanned:
        <copick root>/{session}/{procrun}/ExperimentRuns/Position_*/VoxelSpacing*/*.zarr

    Args:
        session: Copick session name (e.g., "25oct28b")
        procrun: Copick processing run name (e.g., "run001")
        cluster_id: Cluster to connect to (default: 'bruno')

    Returns:
        Dict with structure:
        {
            "base_dir": "/hpc/.../copick/25oct28b/run001",
            "checked_positions": ["Position_1", "Position_2", ...],
            "combinations": {
                "dctf": [5.0, 10.0],
                "denoise": [5.0, 10.0],
                ...
            }
        }
    """
    base_dir = f"{_copick_root(cluster_id)}/{session}/{procrun}"
    expt_dir = f"{base_dir}/ExperimentRuns"

    result = {
        "base_dir": base_dir,
        "checked_positions": [],
        "combinations": {},
    }

    try:
        # One round trip for the whole Position_*/VoxelSpacing*/type.zarr tree.
        zarr_paths = find_paths(expt_dir, "*.zarr", cluster_id=cluster_id, maxdepth=4, entry_type=FIND_TYPE_DIR)

        if not zarr_paths:
            logger.warning(f"No .zarr directories found in {expt_dir}")
            return result

        # Parse the found paths
        # Pattern: .../ExperimentRuns/Position_X/VoxelSpacingY.YYY/type.zarr
        combos: Dict[str, set] = defaultdict(set)
        positions_seen: set = set()

        for line in zarr_paths:
            # Extract path components
            # Example: /hpc/.../ExperimentRuns/Position_14/VoxelSpacing5.006/dctf.zarr
            parts = line.split("/")
            if len(parts) < 4:
                continue

            # Find the Position, VoxelSpacing, and type from the path
            try:
                # Work backwards from the end: type.zarr, VoxelSpacingX, Position_Y
                zarr_name = parts[-1]  # e.g., "dctf.zarr"
                vs_name = parts[-2]  # e.g., "VoxelSpacing5.006"
                pos_name = parts[-3]  # e.g., "Position_14"

                # Validate and extract components
                if not zarr_name.endswith(".zarr"):
                    continue
                if not vs_name.startswith("VoxelSpacing"):
                    continue
                if not pos_name.startswith("Position_"):
                    continue

                # Extract values
                tomo_type = zarr_name[:-5]  # Remove ".zarr"
                vox_str = vs_name.replace("VoxelSpacing", "")
                voxel_size = float(vox_str)

                if tomo_type:
                    combos[tomo_type].add(voxel_size)
                    positions_seen.add(pos_name)

            except (ValueError, IndexError):
                continue

        # Natural sort positions
        def natural_sort_key(s):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]

        result["checked_positions"] = sorted(positions_seen, key=natural_sort_key)

        # Convert sets to sorted lists
        result["combinations"] = {tomo_type: sorted(voxel_sizes) for tomo_type, voxel_sizes in sorted(combos.items())}

        logger.info(
            f"Scanned {len(result['checked_positions'])} positions in {session}/{procrun}, "
            f"found {len(result['combinations'])} tomo types",
        )

        return result

    except Exception as e:
        logger.error(f"Error scanning tomo combos for {session}/{procrun}: {e}")
        result["error"] = str(e)
        return result


@require_http_methods(["GET"])
def get_dynamic_options(request, session_id: str = None) -> JsonResponse:
    """
    Get dynamic dropdown options for Membrane Segmentation form fields.

    Implements cascading dropdown support:
    - copick_session: List of sessions with Copick projects
    - copick_procrun: Runs for selected session (requires copick_session param)
    - tomo_type: Tomo types for selected session/run (requires copick_session, copick_procrun params)
    - tomo_voxel_size: Voxel sizes for selected session/run/type

    Args:
        request: Django HTTP request
        session_id: Optional MSI session ID (not used for membraneseg, but required by router)

    Query Parameters:
        copick_session: Selected Copick session (for dependent fields)
        copick_procrun: Selected Copick run (for dependent fields)
        tomo_type: Selected tomogram type (for dependent fields)

    Returns:
        JsonResponse with field options
    """
    options = {}

    # Get query parameters for cascading dropdowns
    copick_session_param = request.GET.get("copick_session")
    copick_procrun_param = request.GET.get("copick_procrun")
    tomo_type_param = request.GET.get("tomo_type")

    # 1. Get available Copick sessions (sessions with Copick ProcRuns)
    try:
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
        logger.info(f"Found {len(options['copick_session'])} Copick sessions")

    except ProcPlan.DoesNotExist:
        logger.warning("Copick plan (czii-copick) not found")
        options["copick_session"] = []

    # 2. Get Copick runs for selected session
    if copick_session_param:
        try:
            copick_plan = ProcPlan.objects.get(name="czii-copick")
            session_obj = MsiSession.objects.get(name=copick_session_param)

            copick_runs = ProcRun.objects.filter(
                proc_plan=copick_plan,
                msi_session=session_obj,
            ).order_by("-created_at")

            options["copick_procrun"] = [
                {
                    "value": run.name,
                    "label": run.name,
                    "description": f"Created {run.created_at.strftime('%Y-%m-%d %H:%M')}",
                }
                for run in copick_runs
            ]
            logger.info(f"Found {len(options['copick_procrun'])} Copick runs for {copick_session_param}")

        except (ProcPlan.DoesNotExist, MsiSession.DoesNotExist) as e:
            logger.warning(f"Error getting Copick runs: {e}")
            options["copick_procrun"] = []

    # 3. Get tomo types and voxel sizes from remote filesystem
    if copick_session_param and copick_procrun_param:
        try:
            tomo_data = _get_tomo_combos(copick_session_param, copick_procrun_param)
            combinations = tomo_data.get("combinations", {})

            # Build tomo_type options
            options["tomo_type"] = [
                {
                    "value": tomo_type,
                    "label": tomo_type.upper(),
                    "description": f"{len(voxel_sizes)} voxel size(s) available",
                }
                for tomo_type, voxel_sizes in combinations.items()
                if voxel_sizes  # Only show types that have voxel sizes
            ]

            # 4. Get voxel sizes for selected tomo_type
            if tomo_type_param and tomo_type_param in combinations:
                voxel_sizes = combinations[tomo_type_param]
                options["tomo_voxel_size"] = [
                    {
                        "value": voxel_size,
                        "label": f"{voxel_size} Å",
                        "description": f"Voxel size {voxel_size} Angstroms",
                    }
                    for voxel_size in sorted(voxel_sizes)
                ]

            logger.info(
                f"Found {len(options.get('tomo_type', []))} tomo types for "
                f"{copick_session_param}/{copick_procrun_param}",
            )

        except Exception as e:
            logger.error(f"Error getting tomo combos: {e}")
            options["tomo_type"] = []
            options["tomo_voxel_size"] = []

    return JsonResponse(
        {
            "success": True,
            "options": options,
        }
    )


@require_http_methods(["POST"])
def validate_parameters(request) -> JsonResponse:
    """
    Validate membrane segmentation parameters before submission.

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

    # Required fields
    required_fields = ["copick_session", "copick_procrun", "tomo_type", "tomo_voxel_size"]
    for field in required_fields:
        if not params.get(field):
            errors.append(
                {
                    "field": field,
                    "message": f"{field} is required",
                }
            )

    # Validate voxel size
    tomo_voxel_size = params.get("tomo_voxel_size")
    if tomo_voxel_size is not None:
        try:
            voxel_size = float(tomo_voxel_size)
            if voxel_size < 1.0 or voxel_size > 100.0:
                errors.append(
                    {
                        "field": "tomo_voxel_size",
                        "message": "Voxel size must be between 1.0 and 100.0 Angstroms",
                    }
                )
        except (ValueError, TypeError):
            errors.append(
                {
                    "field": "tomo_voxel_size",
                    "message": "Voxel size must be a valid number",
                }
            )

    # Validate threshold if provided
    threshold = params.get("threshold")
    if threshold is not None and threshold != "":
        try:
            float(threshold)
        except (ValueError, TypeError):
            errors.append(
                {
                    "field": "threshold",
                    "message": "Threshold must be a valid number",
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
    Get recommended default parameters for membrane segmentation.

    Note: Membrane segmentation doesn't use MSI session selection,
    so this endpoint returns minimal defaults.

    Args:
        request: Django HTTP request
        session_id: Optional MSI session ID (not used)

    Returns:
        JsonResponse with default parameter values
    """
    return JsonResponse(
        {
            "success": True,
            "defaults": {
                "threshold": 0,
            },
            "session_info": {},
        }
    )


@require_http_methods(["GET"])
def get_processor_metadata(request) -> JsonResponse:
    """
    Get membrane segmentation processor metadata for UI display.

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
                    "Membrane Segmentation runs membrain-seg inference on Copick tomograms "
                    "to generate membrane segmentation volumes. This processor requires an "
                    "existing Copick project with imported tomograms."
                ),
                "category": "Segmentation",
                "docs_url": "https://github.com/teamtomo/membrain-seg",
                "parameter_notes": {
                    "copick_session": "Select the Copick session containing tomograms to process.",
                    "copick_procrun": "Select the Copick processing run within the session.",
                    "tomo_type": "Tomogram type to segment (e.g., dctf, wbp, denoise).",
                    "tomo_voxel_size": "Voxel size of the tomograms in Angstroms.",
                    "threshold": "Optional segmentation threshold. Leave empty for default.",
                },
            },
        }
    )
