"""
Utility functions for workflow views.

This module contains helper functions used across various workflow views,
including data processing, formatting, parsing, and sorting utilities.
"""

import pandas as pd
from processes.models import JobLog
from umbrella_logger import logger

from common import clusterio

from .constants import ENVIRONMENT


def get_base_url():
    """Get the base URL for job tracking based on the environment."""
    if ENVIRONMENT == "staging":
        return "http://umbrella-dev.czbiohub.org/workflow/track_jobs"
    elif ENVIRONMENT == "production":
        return "http://umbrella.czbiohub.org/workflow/track_jobs"
    else:  # development
        return "http://localhost:8000/workflow/track_jobs"


def track_jobs_internal(cluster_id="czii"):
    """
    Fetch job status from SLURM for a specific cluster.

    Args:
        cluster_id (str): Cluster to query ('czii' or 'bruno')

    Returns:
        dict: Dictionary with 'jobs' key containing list of job dicts
    """
    from workflow.agent import StatusChecker

    from .constants import ARETOMO3_SCRIPT_PATH, ARETOMO3_TEMPLATE_PATH

    try:
        checker = StatusChecker(
            cluster_id=cluster_id,
            auth=clusterio.get_auth_service_user(),
            remote_script_dir=ARETOMO3_SCRIPT_PATH,
            local_template_path=ARETOMO3_TEMPLATE_PATH,
        )

        checker.connect()
        output, error = checker.track_jobs(job_name=None, all=True)
        jobs = format_job_output(output) if output else []
        checker.close()

        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error fetching jobs from {cluster_id}: {str(e)}")
        return {"jobs": []}


def store_log(job_name, request, data_sanitized, error, advanced_status=False, job_id=None):
    """
    Store a job log entry in the database.

    Args:
        job_name: Name of the job
        request: Django request object containing user info
        data_sanitized: Sanitized job parameters
        error: Error message or exception
        advanced_status: Whether this is an advanced job
        job_id: Optional job ID
    """
    JobLog.objects.create(
        user=request.user,
        job_name=job_name,
        advanced=advanced_status,
        job_id=job_id,
        parameters=data_sanitized,
        error_message=str(error),
    )


def format_job_output(output):
    """
    Format raw SLURM job output into structured data.

    Args:
        output: Raw SLURM squeue output string (pipe-delimited format)

    Returns:
        List of dictionaries containing parsed job information
    """
    # Split the output into lines
    lines = output.strip().split("\n")
    if not lines:
        return []

    # Extract the header and job details
    # Header format: "JOBID:|PARTITION:|NAME:|USER:|ST:|TIME:|TIMELEFT:|NODES:|NODELIST(REASON)"
    header_line = lines[0]
    job_details = lines[1:]

    # Parse header to get field names (strip trailing ":" and "|")
    header_fields = [field.strip().rstrip(":") for field in header_line.split("|")]

    jobs = []
    for job_line in job_details:
        if not job_line.strip():
            continue

        # Split job data by pipe delimiter
        job_data = job_line.split("|")

        # Handle cases where we don't have enough fields
        if len(job_data) < len(header_fields):
            logger.warning(f"Skipping malformed job line: {job_line}")
            continue

        # Initialize a dictionary for the job info
        job_info = {}

        # Map each field value to its header name
        for i, field_name in enumerate(header_fields):
            if i < len(job_data):
                # Strip whitespace and trailing colon from values
                job_info[field_name] = job_data[i].strip().rstrip(":")
            else:
                job_info[field_name] = ""

        jobs.append(job_info)

    return jobs


def parse_script_output(raw_output):
    """
    Parse the raw output string from the status-check script into a structured dict.

    Expected raw_output example:
        1) Number of raw data .mdoc files: 323
        2) Alignment files in aretomo3:
           run001: 298
        3) SART volumes in aretomo3:
           run001: 296
        4) Denoise volumes in denoise:

    Returns a dict similar to:
        {
            "raw_data_files": 323,
            "alignment_files": {"run001": 298},
            "sart_volumes": {"run001": 296},
            "denoise_volumes": {}
        }
    """
    result = {}
    current_section = None
    for line in raw_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("1)"):
            # e.g., "1) Number of raw data .mdoc files: 323"
            try:
                number = int(stripped.split(":")[-1].strip())
                result["raw_data_files"] = number
            except Exception:
                result["raw_data_files"] = None
        elif stripped.startswith("2)"):
            current_section = "alignment_files"
            result[current_section] = {}
        elif stripped.startswith("3)"):
            current_section = "sart_volumes_aretomo"
            result[current_section] = {}
        elif stripped.startswith("4)"):
            current_section = "denoise_volumes"
            result[current_section] = {}
        else:
            # Lines in the indented sections like "run001: 298"
            if current_section and ":" in stripped:
                try:
                    key, val = stripped.split(":", 1)
                    result[current_section][key.strip()] = int(val.strip())
                except Exception:
                    result[current_section][key.strip()] = val.strip()
    return result


def compute_stats(df: pd.DataFrame) -> list:
    """
    Compute statistics for various metrics in the dataframe.

    Args:
        df: DataFrame containing metrics data

    Returns:
        List of dictionaries with mean, median, and std for each metric
    """
    # Get pixel size for conversion to Ångströms
    pixel_size = df["Pix_Size(A)"].iloc[0]

    # Create columns with Ångström values
    df["Thickness(A)"] = df["Thickness(Pix)"] * pixel_size
    df["Global_Shift(A)"] = df["Global_Shift(Pix)"] * pixel_size
    # Handle Defocus(A) column - if it doesn't exist, we'll skip it in statistics
    # If it exists, process it normally
    if "Defocus(A)" in df.columns:
        try:
            df["Defocus(A)"] = df["Defocus(A)"]
        except Exception as e:
            logger.error(f"Error preprocessing Defocus(A) in compute_stats: {str(e)}")
            df["Defocus(A)"] = 0
    else:
        df["Defocus(A)"] = 0

    if "ExtPhase(Deg)" in df.columns:
        try:
            df["ExtPhase(Deg)"] = df["ExtPhase(Deg)"]
        except Exception as e:
            logger.error(f"Error preprocessing ExtPhase in compute_stats: {str(e)}")
            df["ExtPhase(Deg)"] = 0
    else:
        df["ExtPhase(Deg)"] = 0

    column_mapping = {
        "CTF_Score": "CTF Score",
        "Defocus(A)": "Defocus (Å)",
        "ExtPhase(Deg)": "ExtPhase",
        "CTF_Res(A)": "CTF Resolution (Å)",
        "Thickness(A)": "Thickness (Å)",
        "Tilt_Axis": "Tilt Axis (°)",
        "Global_Shift(A)": "Global Shift (Å)",
        "Bad_Patch_Low": "Bad patch low_angle (fraction)",
        "Bad_Patch_All": "Bad patch all_angle (fraction)",
        "Alpha0": "Alpha Offset (°)",
        "Beta0": "Beta Offset (°)",
    }

    # Select only columns to report (only include columns that exist in the dataframe)
    columns_of_interest = [col for col in column_mapping if col in df.columns]
    stats_df = df[columns_of_interest].agg(["mean", "median", "std"])

    result = []
    for col in columns_of_interest:
        result.append(
            {
                "name": column_mapping[col],
                "mean": round(stats_df[col]["mean"], 3),
                "median": round(stats_df[col]["median"], 3),
                "std": round(stats_df[col]["std"], 3),
            }
        )

    return result


def calculate_metric_ranges(df: pd.DataFrame) -> dict[str, list[float]]:
    """
    Calculate min/max ranges for each metric in the dataframe.

    Args:
        df: DataFrame containing metrics data

    Returns:
        Dictionary mapping metric names to [min, max] ranges
    """
    # Get pixel size for conversion to Ångströms
    pixel_size = df["Pix_Size(A)"].iloc[0]

    # Create temporary columns with Ångström values
    df["Thickness(A)"] = df["Thickness(Pix)"] * pixel_size
    df["Global_Shift(A)"] = df["Global_Shift(Pix)"] * pixel_size
    column_mapping = {
        "Thickness(A)": "thickness",
        "Tilt_Axis": "tilt_axis",
        "Global_Shift(A)": "global_shift",
        "Bad_Patch_Low": "bad_patch_low",
        "Bad_Patch_All": "bad_patch_all",
        "CTF_Res(A)": "ctf_resolution",
        "CTF_Score": "ctf_score",
        "Defocus(A)": "defocus",
        "ExtPhase(Deg)": "extphase",
        "Pix_Size(A)": "pixel_size",
        "Alpha0": "alpha0",
        "Beta0": "beta0",
    }

    ranges = {}
    for csv_column, metric_name in column_mapping.items():
        # Only include defocus if the column exists
        if csv_column == "Defocus(A)" and csv_column not in df.columns:
            continue
        if csv_column == "ExtPhase(Deg)" and csv_column not in df.columns:
            continue
        if csv_column in df.columns:
            if csv_column == "Defocus(A)":
                # Handle Defocus(A) column - it might be 0 if not present in original CSV
                try:
                    # Check if all values are 0 (indicating it was added as default)
                    if df[csv_column].eq(0).all():
                        ranges[metric_name] = [0, 0]
                    else:
                        # Extract the first number from each space-separated value
                        clean_values = df[csv_column].apply(lambda x: float(str(x).strip().split()[0]))
                        ranges[metric_name] = [float(clean_values.min()), float(clean_values.max())]
                except Exception as e:
                    logger.error(f"Error processing {csv_column}: {str(e)}")
                    # Fallback to default range if processing fails
                    ranges[metric_name] = [0, 0]
            elif csv_column == "ExtPhase(Deg)":
                try:
                    # Check if all values are 0 (indicating it was added as default)
                    if df[csv_column].eq(0).all():
                        ranges[metric_name] = [0, 0]
                    else:
                        ranges[metric_name] = [float(df[csv_column].min()), float(df[csv_column].max())]
                except Exception as e:
                    logger.error(f"Error processing {csv_column}: {str(e)}")
                    # Fallback to default range if processing fails
                    ranges[metric_name] = [0, 0]
            else:
                ranges[metric_name] = [float(df[csv_column].min()), float(df[csv_column].max())]
    return ranges


def apply_filters(df, filter_config):
    """
    Apply filters to the dataframe based on filter type (AND/OR) and filter criteria.

    Args:
        df: DataFrame to filter
        filter_config: Dictionary with 'filters' and 'filter_type' keys

    Returns:
        Tuple of (accepted_df, rejected_df)
    """
    # If no filter config or empty filters, return entire dataset
    if not filter_config or "filters" not in filter_config:
        return df, pd.DataFrame(columns=df.columns)

    filters = filter_config["filters"]
    filter_type = filter_config.get("filter_type", "AND")

    if not filters:
        return df, pd.DataFrame(columns=df.columns)

    # Map the filter field names to CSV column names
    column_mapping = {
        "thickness": "Thickness(A)",
        "tilt_axis": "Tilt_Axis",
        "global_shift": "Global_Shift(A)",
        "bad_patch_low": "Bad_Patch_Low",
        "bad_patch_all": "Bad_Patch_All",
        "ctf_resolution": "CTF_Res(A)",
        "ctf_score": "CTF_Score",
        "defocus": "Defocus(A)",
        "extphase": "ExtPhase(Deg)",
        "alpha0": "Alpha0",
        "beta0": "Beta0",
    }

    mask = None
    for field, range_values in filters.items():
        if field not in column_mapping or len(range_values) != 2:
            continue

        column_name = column_mapping[field]

        # Skip defocus filter if the column doesn't exist (since all values are 0)
        if field == "defocus" and column_name not in df.columns:
            continue

        # Skip defocus filter if the column doesn't exist (since all values are 0)
        if field == "extphase" and column_name not in df.columns:
            continue

        min_val, max_val = range_values
        current_mask = (df[column_name] >= min_val) & (df[column_name] <= max_val)

        if mask is None:
            mask = current_mask
        else:
            if filter_type == "AND":
                mask = mask & current_mask
            else:  # OR
                mask = mask | current_mask

    if mask is None:
        return df, pd.DataFrame(columns=df.columns)

    accepted_df = df[mask]
    rejected_df = df[~mask]

    return accepted_df, rejected_df


def natural_position_sort_key(name):
    """
    Custom sort key function for position names.

    Handles names like Position_1, Position_1_1, Position_1_2, etc.

    Args:
        name: Position name string

    Returns:
        List of integers for sorting
    """
    # Remove 'Position_' prefix and split by underscore
    parts = name.replace("Position_", "").split("_")

    # Convert each part to integer, defaulting to 0 if conversion fails
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(0)

    # Pad with zeros to ensure consistent sorting (for cases with different depths)
    while len(numbers) < 3:  # Support up to Position_X_Y_Z
        numbers.append(0)

    return numbers
