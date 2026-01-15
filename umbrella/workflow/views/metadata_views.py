"""
Metadata processing views.

These views handle fetching, processing, and filtering of tomogram metadata
and quality metrics from remote processing directories.
"""

import json
import os
import time
from io import StringIO

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from tem.models import MsiSession
from umbrella_logger import logger

from common import clusterio

from .constants import (
    ARETOMO3_PROCESSING_PATH,
    DATA_COLLECTION_PATH,
    HOSTNAME,
    METADATA_SUMMARY_PATH,
)
from .utils import (
    apply_filters,
    calculate_metric_ranges,
    compute_stats,
    natural_position_sort_key,
    preprocess_csv,
)


def get_metadata_summary(request):
    """
    Fetch and compute summary statistics for tomogram metadata.

    Retrieves metrics and timestamp CSV files from the remote processing directory,
    computes statistics, and returns session metadata including user, project, and grid info.
    """
    session_name = request.GET.get("session_name")
    run_number = request.GET.get("run_number")

    if not session_name or not run_number:
        return JsonResponse({"error": "Missing session_name or run_number"}, status=400)

    base_proc_dir = f"{METADATA_SUMMARY_PATH}{session_name}/{run_number}/"
    metrics_path = os.path.join(base_proc_dir, "TiltSeries_Metrics.csv")
    timestamp_path = os.path.join(base_proc_dir, "TiltSeries_TimeStamp.csv")

    try:
        # Create a persistent SSH connection with optimized parameters
        ssh = clusterio.get_cluster_ssh_connection(cluster_id="czii")

        # Create SFTP client with optimized buffer sizes
        sftp = ssh.open_sftp()
        sftp.get_channel().settimeout(10)
        sftp.get_channel().set_combine_stderr(True)

        try:
            # Combine all file operations into a single batch
            infra_start = time.time()
            try:
                # Use stat instead of listdir for faster checks
                try:
                    sftp.stat(metrics_path)
                    sftp.stat(timestamp_path)
                except FileNotFoundError:
                    return JsonResponse({"error": "Required files not found"}, status=404)

            except Exception as dir_err:
                return JsonResponse({"error": f"Access error: {str(dir_err)}"}, status=404)
            infra_time = time.time() - infra_start

            # Optimize file fetching with larger buffer size and parallel reading
            fetch_start = time.time()
            metrics_content = None
            timestamp_content = None

            # Read files with larger buffer size
            with sftp.open(metrics_path, "r", bufsize=32768) as metrics_file:
                metrics_content = metrics_file.read().decode("utf-8")

            # Process metrics immediately while timestamp is being read
            df = pd.read_csv(StringIO(metrics_content))
            df["Tilt_Series"] = df["Tilt_Series"].str.replace(".mrc", "", regex=False)

            # Note: Defocus(A) column is optional - if not present, it will be skipped in statistics

            # Use natural sort with optimized key function
            df = df.sort_values(
                by="Tilt_Series",
                key=lambda col: pd.Index([int("".join(c for c in str(x) if c.isdigit()) or 0) for x in col]),
            ).reset_index(drop=True)
            fetch_time = time.time() - fetch_start

            # Compute statistics with optimized operations
            compute_start = time.time()
            computed_metrics = compute_stats(df)
            compute_time = time.time() - compute_start

            data_collection_dir = f"{DATA_COLLECTION_PATH}{session_name}/{run_number}/"
            aretomo3_processing_dir = f"{ARETOMO3_PROCESSING_PATH}{session_name}/{run_number}/"

            # Get User, Project, and grid information
            user_name = None
            project_name = None
            grid_name = None
            try:
                try:
                    session = MsiSession.objects.get(name=session_name)
                    logger.info(f"Session: {session}")

                    # Get User name
                    if session.user:
                        user_name = session.user.username
                    # Get Project name
                    if session.project:
                        project_name = session.project.name

                    # Get Grid name
                    if session.grid:
                        grid_name = session.grid.name
                except MsiSession.DoesNotExist:
                    # Session not found, leave the values as None
                    logger.warning(f"No MsiSession found with name: {session_name}")
            except Exception as e:
                logger.warning(f"Error retrieving related information: {str(e)}")

            response = {
                "session_name": session_name,
                "run_number": run_number,
                "num_tomograms": len(df),
                "pixel_size": df["Pix_Size(A)"][0],
                "data_collection_directory": data_collection_dir,
                "aretomo3_processing_directory": aretomo3_processing_dir,
                "computed_metrics": computed_metrics,
                "user_name": user_name,
                "project_name": project_name,
                "grid_name": grid_name,
                "timing": {
                    "infra_access_sec": round(infra_time, 3),
                    "file_fetch_sec": round(fetch_time, 3),
                    "data_compute_sec": round(compute_time, 3),
                },
            }

            return JsonResponse(response, json_dumps_params={"indent": 2})

        finally:
            sftp.close()
            ssh.close()

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

        # Parse filters if provided
        filter_config = json.loads(q) if q else {}

        # Read the CSV file
        base_proc_dir = f"{METADATA_SUMMARY_PATH}{session_name}/{run_number}/"
        metrics_path = os.path.join(base_proc_dir, "TiltSeries_Metrics.csv")
        timestamp_path = os.path.join(base_proc_dir, "TiltSeries_TimeStamp.csv")

        thumbnail_base_url = os.path.join(HOSTNAME, session_name, run_number, "thumbnails/")
        ctf_base_url = os.path.join(HOSTNAME, session_name, run_number, "ctf_thumbnails/")
        print(metrics_path)
        print(timestamp_path)

        merged_df = preprocess_csv(metrics_path, timestamp_path, thumbnail_base_url, ctf_base_url, merge="continue")
        print(merged_df)

        # Create a persistent SSH connection with optimized parameters
        ssh = clusterio.get_cluster_ssh_connection(cluster_id="czii")

        # Create SFTP client with optimized buffer sizes
        sftp = ssh.open_sftp()
        sftp.get_channel().settimeout(10)
        sftp.get_channel().set_combine_stderr(True)

        try:
            # Combine all file operations into a single batch
            infra_start = time.time()
            try:
                # Use stat instead of listdir for faster checks
                try:
                    sftp.stat(metrics_path)
                except FileNotFoundError:
                    return JsonResponse({"error": "Required files not found"}, status=404)
            except Exception as dir_err:
                return JsonResponse({"error": f"Access error: {str(dir_err)}"}, status=404)

            infra_time = time.time() - infra_start

            # Optimize file fetching with larger buffer size and parallel reading
            fetch_start = time.time()
            metrics_content = None
            timestamp_content = None

            # Read files with larger buffer size
            with sftp.open(metrics_path, "r", bufsize=32768) as metrics_file:
                metrics_content = metrics_file.read().decode("utf-8")

            # Process metrics immediately while timestamp is being read
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
            fetch_time = time.time() - fetch_start

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
                    result.append({
                        "name": item_name,
                        "metrics": metrics,
                        "thumbnail_path": item_image_path_to_return,
                        "ctf_path": ctf_thumbnails_path,
                    })

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

        finally:
            sftp.close()
            ssh.close()

    except Exception as e:
        return JsonResponse({"error": f"Error processing metadata: {str(e)}"}, status=500)
