"""
Module for reading magnification from MDOC files on remote clusters.

MDOC files are produced by tomo5 during tilt series acquisition.
This module parses the Magnification field from [ZValue = 0] to
cross-validate against the session's configured magnification.
"""

import re
from typing import Any, Dict, Optional

from umbrella_logger import logger

from common.clusterio import get_cluster_ssh_connection

# assume krios1, but hope to make configurable by Path Types mdoc=>...
DEFAULT_MDOC_DIRECTORY = "/hpc/instruments/czii.krios1/OffloadData"


def parse_mdoc_magnification(content: str) -> Optional[int]:
    """
    Parse the Magnification value from [ZValue = 0] in MDOC file content.

    Args:
        content: Full text content of an MDOC file

    Returns:
        Integer magnification value, or None if not found
    """
    in_zvalue_0 = False
    for line in content.splitlines():
        stripped = line.strip()

        # Detect start of [ZValue = 0] section
        if re.match(r"\[ZValue\s*=\s*0\]", stripped):
            in_zvalue_0 = True
            continue

        # Detect start of next section (any [ZValue or [T)
        if in_zvalue_0 and stripped.startswith("["):
            break

        if in_zvalue_0:
            match = re.match(r"Magnification\s*=\s*(\d+)", stripped)
            if match:
                return int(match.group(1))

    return None


def read_mdoc_magnification(
    msi_session_name: str,
    cluster_id: str = "czii",
    mdoc_base_dir: str = DEFAULT_MDOC_DIRECTORY,
) -> Dict[str, Any]:
    """
    Read the magnification from the first MDOC file in a session directory.

    Connects to the cluster via SSH/SFTP and reads the first .mdoc file
    found in the session directory, parsing the Magnification field from
    [ZValue = 0].

    Args:
        msi_session_name: Name of the MSI session (directory name on cluster)
        cluster_id: Cluster to connect to
        mdoc_base_dir: Base directory containing session MDOC directories

    Returns:
        Dict with structure:
        {
            'success': bool,
            'magnification': Optional[int],
            'mdoc_file': Optional[str],
            'error': Optional[str],
        }
    """
    ssh = None
    sftp = None
    session_dir = f"{mdoc_base_dir}/{msi_session_name}"

    try:
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id)
        sftp = ssh.open_sftp()

        # List directory for .mdoc files
        try:
            entries = sftp.listdir(session_dir)
        except FileNotFoundError:
            return {
                "success": False,
                "magnification": None,
                "mdoc_file": None,
                "error": f"Session directory not found: {session_dir}",
            }
        except PermissionError:
            return {
                "success": False,
                "magnification": None,
                "mdoc_file": None,
                "error": f"Permission denied: {session_dir}",
            }

        mdoc_files = sorted(f for f in entries if f.lower().endswith(".mdoc"))
        if not mdoc_files:
            return {
                "success": False,
                "magnification": None,
                "mdoc_file": None,
                "error": f"No MDOC files found in {session_dir}",
            }

        # Read the first MDOC file
        mdoc_filename = mdoc_files[0]
        mdoc_path = f"{session_dir}/{mdoc_filename}"
        with sftp.open(mdoc_path, "r") as f:
            content = f.read().decode("utf-8", errors="replace")

        magnification = parse_mdoc_magnification(content)
        if magnification is None:
            return {
                "success": False,
                "magnification": None,
                "mdoc_file": mdoc_filename,
                "error": f"No Magnification field found in [ZValue = 0] of {mdoc_filename}",
            }

        logger.info(f"MDOC magnification for {msi_session_name}: {magnification} (from {mdoc_filename})")
        return {
            "success": True,
            "magnification": magnification,
            "mdoc_file": mdoc_filename,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error reading MDOC from {session_dir}: {e}")
        return {
            "success": False,
            "magnification": None,
            "mdoc_file": None,
            "error": str(e),
        }
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
