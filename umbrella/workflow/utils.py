import json

import paramiko
import os
from umbrella_logger import logger
from cryptography.fernet import Fernet
# Other connection details
hostname = '10.50.120.52'
port = 22
username = os.getenv('REMOTE_ID')
password = os.getenv('REMOTE_PASSWORD')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')


def ssh_connect(remote_path, shell=False):
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
    return file_contents.decode('utf-8')




def jsonify(data):
    if data is None:
        raise ValueError("input data is empty, please provide data")
    # print(json.loads(data))
    try:
        json_data = json.loads(data)
        return json_data
    except json.JSONDecodeError as e:
        logger.exception(f"JSONDecodeError: {e}")
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

def encrypt_password(password: str):
    # Convert the password to bytes
    password_bytes = password.encode('utf-8')
    # Encrypt the password
    encrypted_password = cipher_suite.encrypt(password_bytes)
    # Convert the encrypted password to a string
    encrypted_password_str = encrypted_password.decode('utf-8')
    return encrypted_password_str

# Function to decrypt the password
def decrypt_password(encrypted_password: str):
    # Convert the encrypted password to bytes
    encrypted_password_bytes = encrypted_password.encode('utf-8')
    # Decrypt the password
    decrypted_password = cipher_suite.decrypt(encrypted_password_bytes)
    # Convert the decrypted password to a string
    decrypted_password_str = decrypted_password.decode('utf-8')
    return decrypted_password_str