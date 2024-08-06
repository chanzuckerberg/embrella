import json

import paramiko
import os

# Other connection details
hostname = '10.50.120.52'
port = 22
username = 'yongbaek.cho'
password = os.getenv('REMOTE_PASSWORD')

KEYS = ('PixSize',
       'AtBin')


def ssh_connect(remote_path):
    # Check if password is retrieved successfully
    if password is None:
        raise ValueError("Password not found in environment variables. Please set REMOTE_PASSWORD.")

    # Create an SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    # Open an SFTP session
    sftp = ssh.open_sftp()

    # Open the remote file
    with sftp.file(remote_path, 'r') as remote_file:
        file_contents = remote_file.read()

    # Close the SFTP session and SSH client
    sftp.close()
    ssh.close()
    # print(file_contents.decode('utf-8'))
    # print(type(file_contents.decode('utf-8')))

    return file_contents.decode('utf-8')


def jsonify(data):
    if data is None:
        raise ValueError("input data is empty, please provide data")
    # print(json.loads(data))
    try:
        json_data = json.loads(data)
        return json_data
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        raise e


def extract_parameters(json_data, parameter_names):
    if json_data is None:
        raise ValueError("Input data is empty, please provide data")

    extracted_params = {}

    for name in parameter_names:
        value = json_data.get(name)
        if value is None:
            raise ValueError(f"{name} not found in the JSON data")
        extracted_params[name] = value

    return extracted_params