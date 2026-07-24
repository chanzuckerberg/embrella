"""
Module for fetching SLURM job logs from remote clusters.

This module handles:
- Parsing log file paths from SLURM scripts
- Connecting to clusters via SSH
- Reading stdout/stderr log files
- Truncating large logs (>1MB)
- Updating PipeExecution records with log content
"""

import re
from typing import Dict, Optional, Tuple

from django.utils import timezone as django_timezone
from umbrella_logger import logger

from common.clusterio import get_cluster_ssh_connection

# Maximum log size to store (1MB)
MAX_LOG_SIZE = 1024 * 1024  # 1MB in bytes

# Size to keep when truncating (last 800KB)
TRUNCATE_KEEP_SIZE = 800 * 1024


def parse_log_paths_from_script(script_content: str, job_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse SLURM log file paths from script content.

    Extracts #SBATCH -o (stdout) and #SBATCH -e (stderr) directives,
    substituting %j with the actual job_id.

    Args:
        script_content: The full SLURM script content
        job_id: The SLURM job ID to substitute for %j

    Returns:
        Tuple of (stdout_path, stderr_path), either can be None if not found

    Example:
        script = "#SBATCH -o /path/to/JOB%j.out\\n#SBATCH -e /path/to/JOB%j.err"
        paths = parse_log_paths_from_script(script, "123456")
        # Returns: ("/path/to/JOB123456.out", "/path/to/JOB123456.err")
    """
    stdout_path = None
    stderr_path = None

    if not script_content:
        return stdout_path, stderr_path

    # Match #SBATCH -o <path>
    stdout_match = re.search(r"#SBATCH\s+-o\s+(\S+)", script_content)
    if stdout_match:
        stdout_path = stdout_match.group(1).replace("%j", job_id)

    # Match #SBATCH -e <path>
    stderr_match = re.search(r"#SBATCH\s+-e\s+(\S+)", script_content)
    if stderr_match:
        stderr_path = stderr_match.group(1).replace("%j", job_id)

    return stdout_path, stderr_path


def _read_file_content(sftp, remote_path: str, max_size: int = MAX_LOG_SIZE) -> str:
    """
    Internal helper to read a single file with truncation.

    Returns file content or raises FileNotFoundError.
    """
    # Get file size
    file_stat = sftp.stat(remote_path)
    file_size = file_stat.st_size

    if file_size == 0:
        return "(Empty log file)"

    if file_size <= max_size:
        # Small file, read normally
        with sftp.file(remote_path, "r") as remote_file:
            content = remote_file.read()
            return content.decode("utf-8", errors="replace")
    else:
        # Large file, read only the tail
        with sftp.file(remote_path, "r") as remote_file:
            # Seek to near the end
            offset = file_size - TRUNCATE_KEEP_SIZE
            remote_file.seek(offset)
            content = remote_file.read()
            decoded_content = content.decode("utf-8", errors="replace")

            # Add truncation notice
            truncation_notice = (
                f"[LOG TRUNCATED - Original size: {file_size} bytes, showing last {TRUNCATE_KEEP_SIZE} bytes]\n\n"
            )
            return truncation_notice + decoded_content


def read_remote_file_with_truncation(sftp, remote_path: str, max_size: int = MAX_LOG_SIZE) -> str:
    """
    Read a remote file via SFTP, truncating if it exceeds max_size.

    If the file is larger than max_size, keeps only the last portion
    (TRUNCATE_KEEP_SIZE bytes) to show recent output.

    For hetjobs, if the file isn't found with the base job ID, tries with
    '+0' appended (SLURM uses component IDs like 9242+0 for hetjobs).

    Args:
        sftp: Active SFTP session
        remote_path: Path to the file on remote server
        max_size: Maximum size to read before truncating

    Returns:
        File content as string, potentially with truncation notice prepended
    """
    try:
        return _read_file_content(sftp, remote_path, max_size)
    except FileNotFoundError:
        # For hetjobs: SLURM %j expands to "jobid+component" (e.g., 9242+0)
        # Try the hetjob component 0 path if base path not found
        # Pattern: JOB9242_aretomo3.out -> JOB9242+0_aretomo3.out
        hetjob_path = re.sub(r"(JOB\d+)([_.])", r"\1+0\2", remote_path)
        if hetjob_path != remote_path:
            try:
                logger.info(f"Trying hetjob path: {hetjob_path}")
                return _read_file_content(sftp, hetjob_path, max_size)
            except FileNotFoundError:
                pass
        return f"(Log file not found: {remote_path})"
    except Exception as e:
        logger.error(f"Error reading remote file {remote_path}: {e}")
        return f"(Error reading log file: {str(e)})"


def fetch_job_logs(execution) -> Dict[str, any]:
    """
    Fetch SLURM job logs (stdout/stderr) from cluster and update PipeExecution.

    This function:
    1. Determines which cluster the job ran on
    2. Parses log file paths from the script_content
    3. Connects to the cluster via SSH
    4. Reads the log files (with size limits)
    5. Updates the PipeExecution record

    Args:
        execution: PipeExecution instance

    Returns:
        Dictionary with status and any errors:
        {
            'success': bool,
            'stdout_fetched': bool,
            'stderr_fetched': bool,
            'error': Optional[str]
        }
    """

    result = {
        "success": False,
        "stdout_fetched": False,
        "stderr_fetched": False,
        "error": None,
    }

    # Validate execution
    if not execution.job_id:
        result["error"] = "No job_id found in execution"
        execution.log_fetch_error = result["error"]
        execution.logs_fetched_at = django_timezone.now()
        execution.save(update_fields=["log_fetch_error", "logs_fetched_at"])
        return result

    if not execution.script_content:
        result["error"] = "No script_content found in execution"
        execution.log_fetch_error = result["error"]
        execution.logs_fetched_at = django_timezone.now()
        execution.save(update_fields=["log_fetch_error", "logs_fetched_at"])
        return result

    # Determine cluster: prefer the stamp on parameters, else fall back to the software default.
    from processes.services.cluster_resolver import cluster_id_from_parameters, get_default_cluster_id

    cluster_id = cluster_id_from_parameters(execution.parameters, default=None)
    if not cluster_id:
        software = execution.pipe_in_plan.pipe.software
        cluster_id = (
            getattr(software, "default_cluster", None)
            or getattr(software, "cluster", None)
            or get_default_cluster_id()
        )

    logger.info(f"Fetching logs for job {execution.job_id} from cluster {cluster_id}")

    # Parse log paths from script
    stdout_path, stderr_path = parse_log_paths_from_script(
        execution.script_content,
        execution.job_id,
    )

    if not stdout_path and not stderr_path:
        result["error"] = "Could not parse log file paths from script_content"
        execution.log_fetch_error = result["error"]
        execution.logs_fetched_at = django_timezone.now()
        execution.save(update_fields=["log_fetch_error", "logs_fetched_at"])
        return result

    # Connect to cluster and fetch logs
    ssh = None
    sftp = None
    try:
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id)
        sftp = ssh.open_sftp()

        # Fetch stdout
        if stdout_path:
            logger.info(f"Fetching stdout from {stdout_path}")
            execution.stdout_log = read_remote_file_with_truncation(sftp, stdout_path)
            result["stdout_fetched"] = True

        # Fetch stderr
        if stderr_path:
            logger.info(f"Fetching stderr from {stderr_path}")
            execution.stderr_log = read_remote_file_with_truncation(sftp, stderr_path)
            result["stderr_fetched"] = True

        result["success"] = result["stdout_fetched"] or result["stderr_fetched"]
        execution.logs_fetched_at = django_timezone.now()
        execution.log_fetch_error = None
        execution.save(
            update_fields=[
                "stdout_log",
                "stderr_log",
                "logs_fetched_at",
                "log_fetch_error",
            ]
        )

        logger.info(f"Successfully fetched logs for job {execution.job_id}")

    except Exception as e:
        error_msg = f"Error fetching logs: {str(e)}"
        logger.error(f"Error fetching logs for job {execution.job_id}: {e}")
        result["error"] = error_msg
        execution.log_fetch_error = error_msg
        execution.logs_fetched_at = django_timezone.now()
        execution.save(update_fields=["log_fetch_error", "logs_fetched_at"])

    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

    return result
