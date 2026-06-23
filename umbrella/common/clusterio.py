import json
import os
import re
import stat
import subprocess
from fnmatch import fnmatch
from functools import lru_cache

import paramiko
from umbrella_logger import logger


def _get_service_user_auth():
    """
    Lazy-load service user authentication.

    This function loads the SSH key only when actually needed,
    rather than at module import time. This allows Django to start
    and tests to run even if the SSH key is not configured.
    """
    keyfile_path = os.getenv("SLURM_KEYFILE")
    if not keyfile_path:
        raise ValueError(
            "SLURM_KEYFILE environment variable not set. "
            "SSH operations requiring service user authentication will not work.",
        )

    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(keyfile_path)
    except Exception as e:
        raise ValueError(
            f"Failed to load SSH key from {keyfile_path}: {e}. "
            "Check that the file exists and is a valid Ed25519 private key.",
        )

    return {
        "username": os.getenv("SLURM_USER"),
        "pkey": pkey,
    }


# Cached auth - will be populated on first use
_AUTH_SERVICE_USER_CACHE = None


def _get_cached_auth():
    """Get cached service user auth, or load it if not yet cached."""
    global _AUTH_SERVICE_USER_CACHE
    if _AUTH_SERVICE_USER_CACHE is None:
        _AUTH_SERVICE_USER_CACHE = _get_service_user_auth()
    return _AUTH_SERVICE_USER_CACHE


def get_auth_service_user():
    """
    Get the service user authentication credentials.

    Returns a dictionary with 'username' and 'pkey' keys.
    The authentication is cached after the first call.
    """
    return _get_cached_auth()


@lru_cache(maxsize=32)
def _lookup_cluster(cluster_id):
    """Fetch an active Cluster row; raise a clear error if it's missing/inactive.

    Cached per-process; invalidated on Cluster save/delete via signals in stores.models.
    lru_cache does not cache exceptions, so failed lookups are re-attempted.
    """
    from stores.models import Cluster
    try:
        return Cluster.objects.get(cluster_id=cluster_id, is_active=True)
    except Cluster.DoesNotExist:
        raise Exception(f"Cluster '{cluster_id}' not found")


@lru_cache(maxsize=32)
def _cluster_exists(cluster_id):
    """Return True if an active Cluster row exists for this id. Cached like _lookup_cluster."""
    from stores.models import Cluster
    return Cluster.objects.filter(cluster_id=cluster_id, is_active=True).exists()


def clear_cluster_cache():
    """Invalidate the in-process Cluster lookup cache. Called from a post_save/post_delete signal."""
    _lookup_cluster.cache_clear()
    _cluster_exists.cache_clear()


def get_cluster_ssh_connection(cluster_id, auth=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    cluster = _lookup_cluster(cluster_id)

    if auth is None:
        # Use service user auth by default
        auth = _get_cached_auth()
    ssh_config = {
        "hostname": cluster.ssh_hostname,
        "port": cluster.ssh_port,
        "timeout": 10,
        "allow_agent": False,
        "look_for_keys": False,
        "compress": True,
        "banner_timeout": 10,
    }
    ssh_config = {**ssh_config, **auth}
    ssh.connect(**ssh_config)
    return ssh


def read_remote_file(cluster_id, remote_path, auth=None):
    """Read a file from a cluster over SFTP and return its UTF-8 content.

    Args:
        cluster_id: Target cluster (e.g., 'czii', 'bruno').
        remote_path: Absolute path on the cluster filesystem.
        auth: Optional auth dict; defaults to cached service-user auth.

    Returns:
        File content as a UTF-8 string.

    Raises:
        FileNotFoundError: if the remote path does not exist.
    """
    ssh = get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)
    try:
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_path, "r") as remote_file:
                return remote_file.read().decode("utf-8")
        finally:
            sftp.close()
    finally:
        ssh.close()


def jsonify(data):
    if data is None:
        raise ValueError("input data is empty, please provide data")
    # print(json.loads(data))
    try:
        json_data = json.loads(data)
        return json_data
    except json.JSONDecodeError as e:
        logger.exception(f"JSONDecodeError: {e}")
        raise


def extract_parameters(json_data, parameter_names):
    if json_data is None:
        raise ValueError("Input data is empty, please provide data")

    extracted_params = {}
    for name in parameter_names:
        value = json_data["parameters"].get(name)
        if value is None:
            raise ValueError(f"{name} not found in the JSON data")
        extracted_params[name] = value

    return extracted_params


def get_remote_file_metadata(remote_path, cluster_id="czii", auth=None):
    """
    Get file metadata from a remote path via SSH/SFTP.

    Args:
        remote_path (str): Full path to file/directory on remote host
        cluster_id (str): Cluster identifier (default: 'czii')
        auth (dict, optional): Custom authentication credentials

    Returns:
        dict: File metadata with keys:
            - exists (bool): Whether the file exists
            - size_bytes (int): File size in bytes (0 if doesn't exist)
            - modified_time (float): Last modification time as Unix timestamp (None if doesn't exist)
            - is_directory (bool): Whether the path is a directory (None if doesn't exist)
            - error (str, optional): Error message if operation failed

    Example:
        metadata = get_remote_file_metadata('/path/to/file.zarr', 'czii')
        if metadata['exists']:
            print(f"Size: {metadata['size_bytes']} bytes")
    """
    ssh = None
    sftp = None

    try:
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)
        sftp = ssh.open_sftp()

        try:
            stat_info = sftp.stat(remote_path)

            return {
                "exists": True,
                "size_bytes": stat_info.st_size,
                "modified_time": stat_info.st_mtime,
                "is_directory": stat.S_ISDIR(stat_info.st_mode),
                "error": None,
            }

        except FileNotFoundError:
            return {
                "exists": False,
                "size_bytes": 0,
                "modified_time": None,
                "is_directory": None,
                "error": None,
            }

    except Exception as e:
        return {
            "exists": False,
            "size_bytes": 0,
            "modified_time": None,
            "is_directory": None,
            "error": str(e),
        }

    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def resolve_placeholder_and_list_files(template_path, cluster_id="czii", auth=None):
    """
    Resolve a path template with placeholders and list all matching files.

    Takes a path like "/path/to/{run}_Vol.mrc" and:
    1. Lists contents of parent directory ("/path/to/")
    2. Matches files against pattern ("*_Vol.mrc")
    3. Returns metadata for all matching files

    Args:
        template_path (str): Path with {placeholder} syntax (e.g., "/data/{run}_file.txt")
        cluster_id (str): Cluster identifier (default: 'czii')
        auth (dict, optional): Custom authentication credentials

    Returns:
        dict: Result with keys:
            - success (bool): Whether operation succeeded
            - files (list): List of dicts with keys: name, size_bytes, modified_time, full_path
            - total_size (int): Aggregate size of all matched files
            - pattern (str): The glob pattern used for matching
            - parent_dir (str): The parent directory that was listed
            - error (str, optional): Error message if operation failed

    Example:
        result = resolve_placeholder_and_list_files(
            "/hpc/processing/run001/{run}_Vol.mrc",
            'czii'
        )
        if result['success']:
            print(f"Found {len(result['files'])} files, total: {result['total_size']} bytes")
            for file_info in result['files']:
                print(f"  {file_info['name']}: {file_info['size_bytes']} bytes")
    """
    ssh = None
    sftp = None

    try:
        # Handle placeholders in path segments
        # Example: "/a/b/{run}/output.mrc" -> list "/a/b/" for dirs matching pattern, then check for "output.mrc" in each

        # Split path into segments
        path_segments = template_path.split("/")

        # Find the first segment with a placeholder
        placeholder_idx = None
        for i, segment in enumerate(path_segments):
            if "{" in segment and "}" in segment:
                placeholder_idx = i
                break

        if placeholder_idx is None:
            # No placeholder found - shouldn't happen but handle gracefully
            return {
                "success": False,
                "files": [],
                "total_size": 0,
                "pattern": None,
                "parent_dir": None,
                "error": "No placeholder found in path",
            }

        # Parent directory is everything up to (not including) the placeholder segment
        parent_dir = "/".join(path_segments[:placeholder_idx])
        if not parent_dir:
            parent_dir = "/"

        # Remaining path segments after placeholder (including placeholder segment)
        remaining_segments = path_segments[placeholder_idx:]

        # Build glob pattern by replacing {placeholders} with *
        pattern_segments = [re.sub(r"\{[^}]+\}", "*", seg) for seg in remaining_segments]
        relative_pattern = "/".join(pattern_segments)

        logger.info(f"Resolving template: {template_path}")
        logger.info(f"  Parent dir: {parent_dir}")
        logger.info(f"  Relative pattern: {relative_pattern}")

        # Connect to remote host
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)
        sftp = ssh.open_sftp()

        # Check if parent directory exists
        try:
            sftp.stat(parent_dir)
        except FileNotFoundError:
            return {
                "success": False,
                "files": [],
                "total_size": 0,
                "pattern": relative_pattern,
                "parent_dir": parent_dir,
                "error": f"Parent directory does not exist: {parent_dir}",
            }

        # Recursive function to match files against pattern
        def match_files_recursive(current_dir, pattern_parts):
            """Recursively match files against pattern parts."""
            matched = []

            if not pattern_parts:
                return matched

            current_pattern = pattern_parts[0]
            remaining_patterns = pattern_parts[1:]

            try:
                entries = sftp.listdir_attr(current_dir)
            except (FileNotFoundError, PermissionError) as e:
                logger.warning(f"Cannot list directory {current_dir}: {e}")
                return matched

            for entry in entries:
                entry_name = entry.filename
                entry_path = os.path.join(current_dir, entry_name)

                # Check if entry matches current pattern
                if fnmatch(entry_name, current_pattern):
                    if remaining_patterns:
                        # More pattern parts remaining - recurse if this is a directory
                        if stat.S_ISDIR(entry.st_mode):
                            matched.extend(match_files_recursive(entry_path, remaining_patterns))
                    else:
                        # Last pattern part - include if it's a file
                        if not stat.S_ISDIR(entry.st_mode):
                            matched.append(
                                {
                                    "name": entry_name,
                                    "size_bytes": entry.st_size,
                                    "modified_time": entry.st_mtime,
                                    "full_path": entry_path,
                                },
                            )

            return matched

        # Split pattern into parts and match
        pattern_parts = [p for p in pattern_segments if p]  # Remove empty strings
        matched_files = match_files_recursive(parent_dir, pattern_parts)

        total_size = sum(f["size_bytes"] for f in matched_files)

        logger.info(f"  Matched {len(matched_files)} files, total size: {total_size} bytes")

        return {
            "success": True,
            "files": matched_files,
            "total_size": total_size,
            "pattern": relative_pattern,
            "parent_dir": parent_dir,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error resolving placeholder path {template_path}: {str(e)}")
        return {
            "success": False,
            "files": [],
            "total_size": 0,
            "pattern": relative_pattern if "relative_pattern" in locals() else None,
            "parent_dir": parent_dir if "parent_dir" in locals() else None,
            "error": str(e),
        }

    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


# ============================================================================
# SSH Key Setup Functions for One-Time User Authentication
# ============================================================================


def test_ssh_as_user(username, cluster_id):
    """
    Test if the service user can SSH as the specified user on the given cluster.
    This checks if the service user's public key is already in the user's authorized_keys.

    Args:
        username (str): The cluster username to test
        cluster_id (str): The cluster to test ('czii' or 'bruno')

    Returns:
        dict: {
            'can_connect': bool,
            'error': str or None,
            'cluster_id': str,
            'username': str
        }
    """
    if not _cluster_exists(cluster_id):
        return {
            "can_connect": False,
            "error": f"Invalid cluster_id: {cluster_id}",
            "cluster_id": cluster_id,
            "username": username,
        }

    ssh = None
    try:
        # Try to connect as the user using service user's key
        auth = _get_service_user_auth() # Using service user's key
        auth['username'] = username # Connect AS the user
        ssh = get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)

        # Test with a simple command
        stdin, stdout, stderr = ssh.exec_command('echo "test"')
        output = stdout.read().decode("utf-8").strip()

        if output == "test":
            logger.info(f"SSH test successful: service user can connect as {username} on {cluster_id}")
            return {
                "can_connect": True,
                "error": None,
                "cluster_id": cluster_id,
                "username": username,
            }
        else:
            return {
                "can_connect": False,
                "error": "SSH connection succeeded but command test failed",
                "cluster_id": cluster_id,
                "username": username,
            }

    except paramiko.AuthenticationException:
        logger.info(f"SSH setup not complete: service user cannot authenticate as {username} on {cluster_id}")
        return {
            "can_connect": False,
            "error": "SSH key not set up (authentication failed)",
            "cluster_id": cluster_id,
            "username": username,
        }

    except paramiko.SSHException as e:
        logger.error(f"SSH error testing connection as {username} on {cluster_id}: {str(e)}")
        return {
            "can_connect": False,
            "error": f"SSH error: {str(e)}",
            "cluster_id": cluster_id,
            "username": username,
        }

    except Exception as e:
        logger.error(f"Unexpected error testing SSH as {username} on {cluster_id}: {str(e)}")
        return {
            "can_connect": False,
            "error": f"Unexpected error: {str(e)}",
            "cluster_id": cluster_id,
            "username": username,
        }

    finally:
        if ssh:
            ssh.close()


def get_auth_for_user(user, cluster_id):
    """
    Build SSH auth credentials for a Django user on the given cluster.

    Looks up the user's cluster username from UserClusterCredentials and
    returns service-user-key auth bound to that username. Raises
    MissingClusterCredentialsError when no row exists — callers should catch
    this and surface the standard ssh_setup_required 403 contract so the
    frontend opens the SSH setup modal.

    Args:
        user: Authenticated Django User instance.
        cluster_id (str): Target cluster ('czii' or 'bruno').

    Returns:
        tuple: (auth_dict, error_dict_or_none)
            - auth_dict (dict): {"username": str, "pkey": paramiko.Ed25519Key}
              for get_cluster_ssh_connection().
            - error_dict (dict or None): Cluster-validation error, or None on
              success. Missing credentials raise instead of returning an
              error dict.

    Raises:
        MissingClusterCredentialsError: when the user has not set up
            credentials for `cluster_id`.
    """
    from accounts.cluster_usernames import resolve_cluster_username

    if not _cluster_exists(cluster_id):
        return None, {
            "error": f"Invalid cluster_id: {cluster_id}",
            "ssh_setup_required": False,
            "cluster_id": cluster_id,
        }

    cluster_username = resolve_cluster_username(user, cluster_id)
    auth = get_auth_service_user()
    auth = {**auth, "username": cluster_username}
    return auth, None


def setup_ssh_key_for_user(username, password, cluster_id):
    """
    Set up SSH key access for a user by adding the service user's public key
    to their authorized_keys file on the cluster.

    This function:
    1. Reads the service user's public key
    2. Connects to the cluster using the user's password
    3. Creates ~/.ssh directory if needed
    4. Appends service user's public key to ~/.ssh/authorized_keys
    5. Sets proper permissions
    6. Tests the connection to verify setup

    Args:
        username (str): The cluster username
        password (str): The user's password (used only for this setup, never stored)
        cluster_id (str): The cluster to set up ('czii' or 'bruno')

    Returns:
        dict: {
            'success': bool,
            'message': str,
            'can_connect': bool,
            'error': str or None
        }
    """
    if not _cluster_exists(cluster_id):
        return {
            "success": False,
            "message": f"Invalid cluster_id: {cluster_id}",
            "can_connect": False,
            "error": f"Invalid cluster_id: {cluster_id}",
        }

    ssh = None
    sftp = None

    try:
        # Step 1: Read service user's public key
        keyfile_path = os.getenv("SLURM_KEYFILE")
        if not keyfile_path:
            return {
                "success": False,
                "message": "Service user key file not configured",
                "can_connect": False,
                "error": "SLURM_KEYFILE environment variable not set",
            }

        # Generate public key from private key using ssh-keygen
        try:
            # Use ssh-keygen -y to properly derive the public key from the private key
            result = subprocess.run(
                ["ssh-keygen", "-y", "-f", keyfile_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            # ssh-keygen outputs the public key in OpenSSH format
            public_key_str = result.stdout.strip()

            # Add service user comment
            service_user_auth = _get_cached_auth()
            service_user_comment = f" {service_user_auth['username']}@embrella\n"
            public_key_line = public_key_str + service_user_comment

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running ssh-keygen: {e.stderr}")
            return {
                "success": False,
                "message": "Failed to generate public key from private key",
                "can_connect": False,
                "error": e.stderr,
            }
        except Exception as e:
            logger.error(f"Error generating public key: {str(e)}")
            return {
                "success": False,
                "message": "Failed to generate public key",
                "can_connect": False,
                "error": str(e),
            }

        # Step 2: Connect using user's password
        try:
            ssh = get_cluster_ssh_connection(cluster_id=cluster_id,
                                             auth={ 'username': username, 'password': password })
        except paramiko.AuthenticationException:
            return {
                "success": False,
                "message": "Authentication failed. Please check your username and password.",
                "can_connect": False,
                "error": "Invalid credentials",
            }

        # Step 3: Create ~/.ssh directory if needed
        stdin, stdout, stderr = ssh.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
        stdout.channel.recv_exit_status()  # Wait for command to complete

        # Step 4: Check if key already exists in authorized_keys
        stdin, stdout, stderr = ssh.exec_command("cat ~/.ssh/authorized_keys 2>/dev/null")
        existing_keys = stdout.read().decode("utf-8")

        # Extract just the key part (without comment) for comparison
        key_part = public_key_str.strip()

        if key_part in existing_keys:
            logger.info(f"Service user key already exists in {username}'s authorized_keys on {cluster_id}")
        else:
            # Append the public key
            sftp = ssh.open_sftp()
            try:
                # Read existing authorized_keys or create new
                try:
                    with sftp.file(".ssh/authorized_keys", "r") as f:
                        existing_content = f.read().decode("utf-8")
                except FileNotFoundError:
                    existing_content = ""

                # Append new key if not already present
                if key_part not in existing_content:
                    with sftp.file(".ssh/authorized_keys", "a") as f:
                        f.write(public_key_line)
                    logger.info(f"Added service user key to {username}'s authorized_keys on {cluster_id}")

            finally:
                sftp.close()
                sftp = None

        # Step 5: Set proper permissions
        stdin, stdout, stderr = ssh.exec_command("chmod 600 ~/.ssh/authorized_keys")
        stdout.channel.recv_exit_status()

        ssh.close()
        ssh = None

        # Step 6: Test the connection using service user's key
        test_result = test_ssh_as_user(username, cluster_id)

        if test_result["can_connect"]:
            return {
                "success": True,
                "message": f"SSH key setup completed successfully for {cluster_id}",
                "can_connect": True,
                "error": None,
            }
        else:
            return {
                "success": False,
                "message": "Key was added but connection test failed",
                "can_connect": False,
                "error": test_result.get("error", "Connection test failed"),
            }

    except paramiko.SSHException as e:
        logger.error(f"SSH error during key setup for {username} on {cluster_id}: {str(e)}")
        return {
            "success": False,
            "message": f"SSH error: {str(e)}",
            "can_connect": False,
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error during SSH key setup for {username} on {cluster_id}: {str(e)}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "can_connect": False,
            "error": str(e),
        }

    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
