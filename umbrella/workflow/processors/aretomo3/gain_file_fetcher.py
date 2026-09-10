"""
Module for fetching gain reference files from remote clusters.

This module handles:
- Listing a resolved gain directory, narrowed by the kind's FilePattern
- Sorting newest first: by the pattern's {timestamp} capture group, else by mtime

The directory and pattern come from the session (`MsiSession.get_session_dir(GAIN_ROLE)` and
`get_file_pattern(GAIN_ROLE)`); nothing here knows about cameras or clusters beyond the id it is handed.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from stores.models import FilePattern
from umbrella_logger import logger

from common.clusterio import list_files

ALL_FILES_GLOB = "*"
# File-scoped placeholder a gain pattern may capture, e.g. 20251218_093959 -- sorts lexically.
TIMESTAMP_GROUP = "timestamp"
UNKNOWN_TIME = "Unknown"


def _sort_key(entry: Dict[str, Any], groups: Dict[str, str]):
    return groups.get(TIMESTAMP_GROUP, ""), entry["modified_time"]


def _format_mtime(modified_time: float) -> str:
    try:
        return datetime.fromtimestamp(modified_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return UNKNOWN_TIME


def _matching(entries, file_pattern: Optional[FilePattern]):
    """(entry, capture groups) for each non-hidden entry the pattern accepts."""
    for entry in entries:
        name = entry["name"]
        if name.startswith("."):
            continue
        if file_pattern is None:
            yield entry, {}
            continue
        groups = file_pattern.match(name)
        if groups is not None:
            yield entry, groups


def list_gain_files(
    gain_directory: str,
    *,
    cluster_id: str,
    file_pattern: Optional[FilePattern] = None,
) -> Dict[str, Any]:
    """
    List gain reference files in a resolved directory, newest first.

    Args:
        gain_directory: Resolved remote directory -- resolve it from the session, never assemble it here.
        cluster_id: Cluster to connect to.
        file_pattern: The kind's filename convention. None lists every file, ordered by mtime.

    Returns:
        Dict with structure:
        {
            'success': bool,
            'files': [
                {
                    'filename': '20251218_093959_EER_GainReference.gain',
                    'modified_time': '2025-12-18 09:40:00',
                    'size_bytes': 12345678,
                },
                ...
            ],
            'directory': '/path/to/gain/files/',
            'error': Optional[str]
        }
    """
    list_glob = file_pattern.list_glob if file_pattern else ALL_FILES_GLOB
    listing = list_files(gain_directory, list_glob, cluster_id=cluster_id)
    if not listing["success"]:
        return {
            "success": False,
            "files": [],
            "directory": gain_directory,
            "error": listing.get("error"),
        }

    matched = sorted(_matching(listing["files"], file_pattern), key=lambda pair: _sort_key(*pair), reverse=True)
    gain_files = [
        {
            "filename": entry["name"],
            "modified_time": _format_mtime(entry["modified_time"]),
            "size_bytes": entry["size_bytes"],
        }
        for entry, _ in matched
    ]

    logger.info(f"Found {len(gain_files)} gain files in {gain_directory}")
    return {
        "success": True,
        "files": gain_files,
        "directory": gain_directory,
        "error": None,
    }
