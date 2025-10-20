import json
import os

import paramiko
from umbrella_logger import logger

AUTH_SERVICE_USER = {
    'username': os.getenv('SLURM_USER'),
    'pkey': paramiko.Ed25519Key.from_private_key_file(os.getenv('SLURM_KEYFILE')),
}

CLUSTER_DETAILS = {
    'czii': {
        'hostname': "10.50.120.90",
        'port': 22,
        'auth': AUTH_SERVICE_USER,
    },
    'bruno': {
        'hostname': "192.168.98.229",
        'port': 22,
        'auth': {},
    },
}

def get_cluster_ssh_connection(cluster_id, auth=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if cluster_id not in CLUSTER_DETAILS:
        raise Exception(f"Cluster '{cluster_id}' not found")

    cluster_info = CLUSTER_DETAILS[cluster_id]
    if auth is None:
        auth = cluster_info['auth']
    ssh_config = {
        'hostname': cluster_info['hostname'],
        'port': cluster_info['port'],
        'timeout': 10,
        'allow_agent': False,
        'look_for_keys': False,
        'compress': True,
        'banner_timeout': 10,
    }
    ssh_config = {**ssh_config, **auth}
    ssh.connect(**ssh_config)
    return ssh

def ssh_connect(remote_path, shell=False):
    # Create an SSH client

    ssh = get_cluster_ssh_connection(cluster_id='czii')

    # Open an SFTP session
    sftp = ssh.open_sftp()

    # Open the remote file
    with sftp.file(remote_path, 'r') as remote_file:
        file_contents = remote_file.read()

    # Close the SFTP session and SSH client
    sftp.close()
    ssh.close()
    return file_contents.decode('utf-8')


def ssh_connect_bruno(remote_path, shell=False):
    # Create an SSH client
    ssh = get_cluster_ssh_connection(cluster_id='bruno', auth=AUTH_SERVICE_USER)

    # Open an SFTP session
    sftp = ssh.open_sftp()

    # Open the remote file
    with sftp.file(remote_path, 'r') as remote_file:
        file_contents = remote_file.read()

    # Close the SFTP session and SSH client
    sftp.close()
    ssh.close()
    return file_contents.decode('utf-8')


def ssh_file_exists(remote_path):
    """
    Check if a file exists on the remote server.

    Args:
        remote_path: The path to the file on the remote server

    Returns:
        bool: True if the file exists, False otherwise
    """
    # Create an SSH client
    ssh = get_cluster_ssh_connection(cluster_id='czii')

    # Open an SFTP session
    sftp = ssh.open_sftp()

    try:
        # Try to get file attributes
        sftp.stat(remote_path)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking if file exists: {str(e)}")
        raise
    finally:
        # Close the SFTP session and SSH client
        sftp.close()
        ssh.close()


def ssh_list_directory(remote_dir):
    """
    List the contents of a directory on the remote server.

    Args:
        remote_dir: The path to the directory on the remote server

    Returns:
        list: A list of file and directory names in the directory
    """
    # Create an SSH client
    ssh = get_cluster_ssh_connection(cluster_id='czii')

    # Open an SFTP session
    sftp = ssh.open_sftp()

    try:
        # List the directory contents
        return sftp.listdir(remote_dir)
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        raise
    finally:
        # Close the SFTP session and SSH client
        sftp.close()
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
        value = json_data['parameters'].get(name)
        if value is None:
            raise ValueError(f"{name} not found in the JSON data")
        extracted_params[name] = value

    return extracted_params
