"""
Module for fetching gain reference files from remote clusters.

This module handles:
- Listing gain files from the microscope gain directory
- Sorting by modification time (most recent first)
"""

from datetime import datetime, timezone
from typing import Any, Dict

from umbrella_logger import logger

from common.clusterio import get_cluster_ssh_connection

# Default gain directory for CZII krios1 microscope
DEFAULT_GAIN_DIRECTORY = "/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"


def _format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string like '11.8 MB' or '1.2 GB'
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def list_gain_files(
    cluster_id: str = "czii",
    gain_directory: str = DEFAULT_GAIN_DIRECTORY,
) -> Dict[str, Any]:
    """
    List gain reference files from the remote cluster.

    Connects to the cluster via SSH/SFTP and lists gain files in the
    specified directory, sorted by modification time (most recent first).

    Args:
        cluster_id: Cluster to connect to ('czii' or 'bruno')
        gain_directory: Path to the gain files directory

    Returns:
        Dict with structure:
        {
            'success': bool,
            'files': [
                {
                    'filename': 'SuperRef_127684.mrc',
                    'modified_time': '2024-01-15 14:30:00',
                    'size_bytes': 12345678,
                    'size_human': '11.8 MB',
                },
                ...
            ],
            'directory': '/path/to/gain/files/',
            'error': Optional[str]
        }

    Example:
        result = list_gain_files('czii')
        if result['success']:
            for file_info in result['files']:
                print(f"{file_info['filename']} - {file_info['size_human']}")
    """
    ssh = None
    sftp = None

    try:
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id)
        sftp = ssh.open_sftp()

        # List directory with attributes
        try:
            entries = sftp.listdir_attr(gain_directory)
        except FileNotFoundError:
            return {
                "success": False,
                "files": [],
                "directory": gain_directory,
                "error": f"Directory not found: {gain_directory}",
            }
        except PermissionError:
            return {
                "success": False,
                "files": [],
                "directory": gain_directory,
                "error": f"Permission denied: {gain_directory}",
            }

        # Filter for gain files and collect metadata
        gain_files = []
        for entry in entries:
            filename = entry.filename

            # Skip hidden files and directories
            if filename.startswith("."):
                continue

            # Check if it's a regular file with valid extension
            # st_mode check: S_ISREG would be proper, but simpler to just check it's not a dir
            # by checking if it has a reasonable size
            if entry.st_size == 0:
                continue
            if not filename.lower().endswith(".gain"):
                continue

            try:
                mod_time = datetime.fromtimestamp(entry.st_mtime, tz=timezone.utc)
                mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                mod_time_str = "Unknown"
            size_bytes = entry.st_size
            size_human = _format_file_size(size_bytes)

            gain_files.append(
                {
                    "filename": filename,
                    "modified_time": mod_time_str,
                    "modified_timestamp": entry.st_mtime,
                    "size_bytes": size_bytes,
                    "size_human": size_human,
                }
            )

        # Sort by modification time (most recent first)
        gain_files.sort(key=lambda x: x["modified_timestamp"], reverse=True)
        for file_info in gain_files:
            del file_info["modified_timestamp"]

        logger.info(f"Found {len(gain_files)} gain files in {gain_directory}")
        return {
            "success": True,
            "files": gain_files,
            "directory": gain_directory,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error listing gain files from {gain_directory}: {e}")
        return {
            "success": False,
            "files": [],
            "directory": gain_directory,
            "error": str(e),
        }
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
