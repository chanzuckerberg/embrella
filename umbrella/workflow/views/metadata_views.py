"""
Metadata processing views.

These views handle fetching, processing, and filtering of tomogram metadata
and quality metrics from remote processing directories.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from io import StringIO

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from processes.services.cluster_resolver import cluster_id_for_run
from stores.models import Cluster, resolve_review_path
from tem.models import MsiSession
from umbrella_logger import logger

from common.httpio import fetch_remote_text
from common.sorting import natural_sort_key

from .utils import (
    apply_filters,
    calculate_metric_ranges,
    compute_stats,
)

# This page reads AreTomo3 outputs only: the metrics CSV and the thumbnails the
# reformat step writes next to the volumes.
PROC_SOFTWARE = "aretomo3"
METRICS_CSV = "TiltSeries_Metrics.csv"

# Tilt_Series is the stack name `{stem}.mrc`; thumbnails are `{stem}.jpeg`
STACK_EXT = ".mrc"
THUMB_EXT = ".jpeg"

FRAMES_ROLE = "frames"
NO_DIR = "."  # get_session_dir's "software emits no such data" answer

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500


class ThumbKind(StrEnum):
    """Subdirectories mrc_to_zarr_and_thumbnails.sh writes under the run directory."""

    THUMBNAILS = "thumbnails"
    CTF = "ctf_thumbnails"


class RunLookupError(Exception):
    """The request names a run this server cannot locate."""

    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class RunLocation:
    cluster: Cluster
    msi_session: MsiSession
    run_number: str


def _locate_run(request):
    """Cluster, session and run named by the query string."""
    session_name = request.GET.get("session_name")
    run_number = request.GET.get("run_number")
    if not session_name or not run_number:
        raise RunLookupError("Missing session_name or run_number", HTTP_BAD_REQUEST)

    cluster_id = request.GET.get("cluster_id") or cluster_id_for_run(session_name, run_number)
    cluster = Cluster.objects.filter(cluster_id=cluster_id, is_active=True).first()
    if cluster is None:
        raise RunLookupError(f"Unknown cluster_id: {cluster_id}", HTTP_BAD_REQUEST)

    msi_session = MsiSession.objects.filter(name=session_name).first()
    if msi_session is None:
        raise RunLookupError(f"Session not found: {session_name}", HTTP_NOT_FOUND)

    return RunLocation(cluster, msi_session, run_number)


def _review_path(loc, kind, **context):
    return resolve_review_path(
        kind,
        loc.cluster,
        msi_session=loc.msi_session,
        proc_software=PROC_SOFTWARE,
        proc_run=loc.run_number,
        **context,
    )


def _metrics_url(loc):
    # The server fetches the CSV itself, so use the in-network base.
    return _review_path(loc, "proc_url", backend_fetch=True) + METRICS_CSV


def _thumb_url(loc, kind):
    return _review_path(loc, "thumb_url", thumb_kind=kind.value)


def _frames_dir(msi_session):
    """Where this session's frames were collected, or None when its software emits none."""
    frames_dir = msi_session.get_session_dir(FRAMES_ROLE)
    return None if frames_dir == NO_DIR else frames_dir


def _read_metrics(loc):
    """The metrics CSV keyed by AreTomo3 stem. Raises FileNotFoundError when absent."""
    df = pd.read_csv(StringIO(fetch_remote_text(_metrics_url(loc))))
    df["Tilt_Series"] = df["Tilt_Series"].str.removesuffix(STACK_EXT)
    return df


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def get_metadata_summary(request):
    """
    Fetch and compute summary statistics for tomogram metadata.

    Retrieves the metrics CSV over HTTP from the processing directory served by
    Caddy, computes statistics, and returns session metadata including user,
    project, and grid info.
    """
    try:
        loc = _locate_run(request)

        try:
            df = _read_metrics(loc)
        except FileNotFoundError:
            return _error("Required files not found", HTTP_NOT_FOUND)

        # Note: Defocus(A) column is optional - if not present, it will be skipped in statistics

        # Use natural sort with optimized key function
        df = df.sort_values(
            by="Tilt_Series",
            key=lambda col: pd.Index([int("".join(c for c in str(x) if c.isdigit()) or 0) for x in col]),
        ).reset_index(drop=True)

        # Compute statistics with optimized operations
        computed_metrics = compute_stats(df)

        msi_session = loc.msi_session
        user_name = msi_session.user.username if msi_session.user else None
        project_name = msi_session.project.name if msi_session.project else None
        grid_name = msi_session.grid.name if msi_session.grid else None

        response = {
            "session_name": msi_session.name,
            "run_number": loc.run_number,
            "cluster": loc.cluster.cluster_id,
            "num_tomograms": len(df),
            "pixel_size": df["Pix_Size(A)"][0],
            "data_collection_directory": _frames_dir(msi_session),
            "aretomo3_processing_directory": _review_path(loc, "proc_dir"),
            "computed_metrics": computed_metrics,
            "user_name": user_name,
            "project_name": project_name,
            "grid_name": grid_name,
        }

        return JsonResponse(response, json_dumps_params={"indent": 2})

    except RunLookupError as e:
        return _error(str(e), e.status)
    except Exception as e:
        logger.error(f"Error processing metadata: {str(e)}")
        return _error(f"Error processing metadata: {str(e)}", HTTP_SERVER_ERROR)


@require_http_methods(["GET"])
def get_metadata_viz_data(request):
    """
    Fetch and filter tomogram visualization data with metrics.

    Returns detailed per-tomogram metrics with thumbnail paths, applying
    optional filters and sorting. Results are split into accepted and rejected sets.
    """
    try:
        loc = _locate_run(request)

        q = request.GET.get("q", {})
        sort_by = request.GET.get("sort_by", None)
        sort_direction = request.GET.get("sort_direction", "asc")

        # Parse filters if provided
        filter_config = json.loads(q) if q else {}

        thumbnail_base_url = _thumb_url(loc, ThumbKind.THUMBNAILS)
        ctf_base_url = _thumb_url(loc, ThumbKind.CTF)

        try:
            df = _read_metrics(loc)
        except FileNotFoundError:
            return _error("Required files not found", HTTP_NOT_FOUND)

        logger.info(f"Total positions in CSV before filtering: {len(df)}")

        # Required columns (excluding Defocus(A) and ExtPhase(Deg) which are optional)
        required_columns = [
            "Tilt_Series",
            "Thickness(Pix)",
            "Tilt_Axis",
            "Global_Shift(Pix)",
            "Bad_Patch_Low",
            "Bad_Patch_All",
            "CTF_Res(A)",
            "CTF_Score",
            "Pix_Size(A)",
            "Alpha0",
            "Beta0",
        ]

        # Check for missing required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")

        # Add Defocus(A) column if it doesn't exist (set to 0)
        if "Defocus(A)" not in df.columns:
            df["Defocus(A)"] = 0
            logger.info("Defocus(A) column not found in CSV, setting to 0")

        #  Add ExtPhase column if it doesn't exist (set to 0)
        if "ExtPhase(Deg)" not in df.columns:
            df["ExtPhase(Deg)"] = 0
            logger.info("ExtPhase(Deg) column not found in CSV, setting to 0")

        # Thumbnails are named after the stem, e.g. thumbnails/Position_8_ts_011.mrc.jpeg
        df["thumbnail_path"] = thumbnail_base_url + df["Tilt_Series"] + THUMB_EXT
        df["ctf_thumbnails_path"] = ctf_base_url + df["Tilt_Series"] + THUMB_EXT

        df = df.sort_values(
            by="Tilt_Series",
            key=lambda col: col.map(natural_sort_key),
        ).reset_index(drop=True)

        # Calculate metric ranges before applying filters
        metric_ranges = calculate_metric_ranges(df)

        # Apply filters if provided
        accepted_df, rejected_df = apply_filters(df, filter_config)

        # Prepare the result lists for both accepted and rejected
        def prepare_result_list(df, apply_sorting=False):
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.iterrows():
                metrics = {
                    "thickness": float(row["Thickness(A)"]),
                    "tilt_axis": float(row["Tilt_Axis"]),
                    "global_shift": float(row["Global_Shift(A)"]),
                    "bad_patch_low": float(row["Bad_Patch_Low"]),
                    "bad_patch_all": float(row["Bad_Patch_All"]),
                    "ctf_resolution": float(row["CTF_Res(A)"]),
                    "ctf_score": float(row["CTF_Score"]),
                    "defocus": float(row["Defocus(A)"]),
                    "extphase": float(row["ExtPhase(Deg)"]),
                    "pixel_size": float(row["Pix_Size(A)"]),
                    "alpha0": float(row["Alpha0"]),
                    "beta0": float(row["Beta0"]) if not pd.isna(row["Beta0"]) else float("nan"),
                }
                result.append(
                    {
                        "name": str(row["Tilt_Series"]),
                        "metrics": metrics,
                        "thumbnail_path": row["thumbnail_path"],
                        "ctf_path": row["ctf_thumbnails_path"],
                    }
                )

            # Apply sorting if requested
            if apply_sorting and sort_by and sort_by != "Select Metric":
                # Map frontend metric names to the actual keys in the metrics dictionary
                metric_key_mapping = {
                    "thickness": "thickness",
                    "tilt_axis": "tilt_axis",
                    "global_shift": "global_shift",
                    "bad_patch_low": "bad_patch_low",
                    "bad_patch_all": "bad_patch_all",
                    "ctf_resolution": "ctf_resolution",
                    "ctf_score": "ctf_score",
                    "defocus": "defocus",
                    "extphase": "extphase",
                    "alpha0": "alpha0",
                    "beta0": "beta0",
                }

                metric_key = metric_key_mapping.get(sort_by)
                if metric_key:
                    # Sort by the selected metric
                    result.sort(
                        key=lambda x: x["metrics"].get(metric_key, 0),
                        reverse=(sort_direction.lower() == "desc"),
                    )

            return result

        accepted_results = prepare_result_list(accepted_df, apply_sorting=True)
        rejected_results = prepare_result_list(rejected_df)

        # The final response
        response_data = {
            "session_name": loc.msi_session.name,
            "run_number": loc.run_number,
            "total_accepted": len(accepted_results),
            "total_rejected": len(rejected_results),
            "filters_applied": {
                "filters": filter_config.get("filters"),
                "filter_type": filter_config.get("filter_type", "AND").upper(),
            },
            "metric_ranges": metric_ranges,
            "accepted_results": accepted_results,
            "rejected_results": rejected_results,
        }

        return JsonResponse(response_data, json_dumps_params={"indent": 2})

    except RunLookupError as e:
        return _error(str(e), e.status)
    except Exception as e:
        return _error(f"Error processing metadata: {str(e)}", HTTP_SERVER_ERROR)
