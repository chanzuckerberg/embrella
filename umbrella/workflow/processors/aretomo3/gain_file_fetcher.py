"""
Module for fetching gain reference files from remote clusters.

This module handles:
- Listing gain files from the microscope gain directory
- Sorting by modification time (most recent first)
"""

from datetime import datetime, timezone
from typing import Any, Dict

from umbrella_logger import logger

from common.clusterio import list_files

# Default gain directory for CZII krios1 microscope
# TODO: gain is a DataKind and dir depends on instrument and software. Resolve by taking in session or session plan to resolve directory
DEFAULT_GAIN_DIRECTORY = "/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"


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
                },
                ...
            ],
            'directory': '/path/to/gain/files/',
            'error': Optional[str]
        }
    """
    listing = list_files(gain_directory, cluster_id=cluster_id)
    if not listing["success"]:
        return {
            "success": False,
            "files": [],
            "directory": gain_directory,
            "error": listing["error"],
        }

    gain_files = []
    for entry in sorted(listing["files"], key=lambda f: f["modified_time"], reverse=True):
        filename = entry["name"]
        if filename.startswith(".") or not filename.lower().endswith(".gain"):
            continue
        # TODO: sort by time with filepattern entry capture group. Issue #722
        try:
            mod_time = datetime.fromtimestamp(entry["modified_time"], tz=timezone.utc)
            mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            mod_time_str = "Unknown"

        gain_files.append(
            {
                "filename": filename,
                "modified_time": mod_time_str,
                "size_bytes": entry["size_bytes"],
            }
        )

    logger.info(f"Found {len(gain_files)} gain files in {gain_directory}")
    return {
        "success": True,
        "files": gain_files,
        "directory": gain_directory,
        "error": None,
    }
