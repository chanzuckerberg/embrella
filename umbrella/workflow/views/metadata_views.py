"""
Metadata processing views.

These views handle fetching, processing, and filtering of tomogram metadata
and quality metrics from remote processing directories.
"""

import json
from io import StringIO

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from processes.services.cluster_resolver import cluster_id_for_run
from stores.models import Cluster, resolve_review_path
from tem.models import MsiSession
from umbrella_logger import logger

from common.httpio import fetch_remote_text

from .constants import DATA_COLLECTION_PATH
from .utils import (
    apply_filters,
    calculate_metric_ranges,
    compute_stats,
    natural_position_sort_key,
)


def get_metadata_summary(request):
    """
    Fetch and compute summary statistics for tomogram metadata.

    Retrieves the metrics CSV over HTTP from the processing directory served by
    Caddy, computes statistics, and returns session metadata including user,
    project, and grid info.
    """
    session_name = request.GET.get("session_name")
    run_number = request.GET.get("run_number")

    if not session_name or not run_number:
        return JsonResponse({"error": "Missing session_name or run_number"}, status=400)

    cluster_id = request.GET.get("cluster_id") or cluster_id_for_run(session_name, run_number)

    try:
        cluster = Cluster.objects.get(cluster_id=cluster_id, is_active=True)
    except Cluster.DoesNotExist:
        return JsonResponse({"error": f"Unknown cluster_id: {cluster_id}"}, status=400)

    try:
        msi_session = MsiSession.objects.get(name=session_name)
    except MsiSession.DoesNotExist:
        return JsonResponse({"error": f"Session not found: {session_name}"}, status=404)

    # Filesystem path is kept only for display; the CSV is fetched over HTTP
    base_proc_dir = resolve_review_path(
        "proc_dir",
        cluster,
        msi_session=msi_session,
        proc_software="aretomo3",
        proc_run=run_number,
    )
    base_proc_url = resolve_review_path(
        "proc_url",
        cluster,
        msi_session=msi_session,
        proc_software="aretomo3",
        proc_run=run_number,
        backend_fetch=True,
    )
    metrics_url = f"{base_proc_url}TiltSeries_Metrics.csv"

    try:
        # Fetch the metrics CSV over HTTP from the Caddy file server.
        try:
            metrics_content = fetch_remote_text(metrics_url)
        except FileNotFoundError:
            return JsonResponse({"error": "Required files not found"}, status=404)

        df = pd.read_csv(StringIO(metrics_content))
        df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)

        # Note: Defocus(A) column is optional - if not present, it will be skipped in statistics

        # Use natural sort with optimized key function
        df = df.sort_values(
            by="Tilt_Series",
            key=lambda col: pd.Index([int("".join(c for c in str(x) if c.isdigit()) or 0) for x in col]),
        ).reset_index(drop=True)

        # Compute statistics with optimized operations
        computed_metrics = compute_stats(df)

        data_collection_dir = f"{DATA_COLLECTION_PATH}{session_name}/{run_number}/"
        aretomo3_processing_dir = base_proc_dir

        user_name = msi_session.user.username if msi_session.user else None
        project_name = msi_session.project.name if msi_session.project else None
        grid_name = msi_session.grid.name if msi_session.grid else None

        response = {
            "session_name": session_name,
            "run_number": run_number,
            "cluster": cluster.cluster_id,
            "num_tomograms": len(df),
            "pixel_size": df["Pix_Size(A)"][0],
            "data_collection_directory": data_collection_dir,
            "aretomo3_processing_directory": aretomo3_processing_dir,
            "computed_metrics": computed_metrics,
            "user_name": user_name,
            "project_name": project_name,
            "grid_name": grid_name,
        }

        return JsonResponse(response, json_dumps_params={"indent": 2})

    except Exception as e:
        logger.error(f"Error processing metadata: {str(e)}")
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def get_metadata_viz_data(request):
    """
    Fetch and filter tomogram visualization data with metrics.

    Returns detailed per-tomogram metrics with thumbnail paths, applying
    optional filters and sorting. Results are split into accepted and rejected sets.
    """
    try:
        # Get request parameters
        session_name = request.GET.get("session_name")
        run_number = request.GET.get("run_number")
        q = request.GET.get("q", {})

        # Get sorting parameters
        sort_by = request.GET.get("sort_by", None)
        sort_direction = request.GET.get("sort_direction", "asc")

        if not session_name or not run_number:
            return JsonResponse({"error": "Missing session_name or run_number"}, status=400)

        cluster_id = request.GET.get("cluster_id") or cluster_id_for_run(session_name, run_number)

        try:
            cluster = Cluster.objects.get(cluster_id=cluster_id, is_active=True)
        except Cluster.DoesNotExist:
            return JsonResponse({"error": f"Unknown cluster_id: {cluster_id}"}, status=400)

        try:
            msi_session = MsiSession.objects.get(name=session_name)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": f"Session not found: {session_name}"}, status=404)

        # Parse filters if provided
        filter_config = json.loads(q) if q else {}

        # Resolve cluster-/scope-aware thumbnail URLs.
        thumbnail_base_url = resolve_review_path(
            "thumb_url",
            cluster,
            msi_session=msi_session,
            proc_run=run_number,
            thumb_kind="thumbnails",
        )
        ctf_base_url = resolve_review_path(
            "thumb_url",
            cluster,
            msi_session=msi_session,
            proc_run=run_number,
            thumb_kind="ctf_thumbnails",
        )

        base_proc_url = resolve_review_path(
            "proc_url",
            cluster,
            msi_session=msi_session,
            proc_software="aretomo3",
            proc_run=run_number,
            backend_fetch=True,
        )
        metrics_url = f"{base_proc_url}TiltSeries_Metrics.csv"

        # Fetch the metrics CSV over HTTP from the Caddy file server.
        try:
            metrics_content = fetch_remote_text(metrics_url)
        except FileNotFoundError:
            return JsonResponse({"error": "Required files not found"}, status=404)

        df = pd.read_csv(StringIO(metrics_content))
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

        df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)

        # Add thumbnail paths directly to the dataframe
        df["thumbnail_path"] = df["Tilt_Series"].apply(
            lambda ts: f"{thumbnail_base_url}{ts}.jpeg",
        )
        df["ctf_thumbnails_path"] = df["Tilt_Series"].apply(
            lambda ts: f"{ctf_base_url}{ts}.jpeg",
        )

        # Use the new custom sorting function
        df = df.sort_values(
            by="Tilt_Series",
            key=lambda col: col.map(natural_position_sort_key),
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
                item_name = str(row["Tilt_Series"])
                image_path = row.get("thumbnail_path", None)
                ctf_path = row.get("ctf_thumbnails_path", None)

                item_image_path_to_return = image_path
                ctf_thumbnails_path = ctf_path
                if image_path is not None:
                    logger.info(
                        f"[METADATA_VIZ_DEBUG] Item: {item_name}, Raw 'thumbnail_path' from row.get(): '{image_path}' (type: {type(image_path)})",
                    )
                else:
                    logger.info(
                        "[METADATA_VIZ_DEBUG] 'thumbnail_path' column MISSING in df passed to prepare_result_list.",
                    )

                if ctf_path is not None:
                    logger.info(
                        f"[METADATA_VIZ_DEBUG] Item: {item_name}, Raw 'ctf_thumbnails_path' from row.get(): '{ctf_path}' (type: {type(ctf_path)})",
                    )
                else:
                    logger.info(
                        "[METADATA_VIZ_DEBUG] 'ctf_thumbnails_path' column MISSING in df passed to prepare_result_list.",
                    )
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
                        "name": item_name,
                        "metrics": metrics,
                        "thumbnail_path": item_image_path_to_return,
                        "ctf_path": ctf_thumbnails_path,
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

        # If no filters were applied, use the entire dataset as the result
        has_filters = filter_config and "filters" in filter_config and filter_config["filters"]
        if not has_filters:
            result = prepare_result_list(df, apply_sorting=True)
        else:
            result = []

        # The final response
        response_data = {
            "session_name": session_name,
            "run_number": run_number,
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

    except Exception as e:
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)
