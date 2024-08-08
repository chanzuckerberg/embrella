import paramiko
import os

ARETOMO3_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/scripts/run_aretomo_sta_pipeline.sh'
# ARETOMO3_SCRIPT_PATH = '/hpc/projects/group.czii/krios1.processing/aretomo3/scripts/test.sh'


class Aretomo3(object):
    def __init__(self, hostname, port, username, password, script_path):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.script_path = script_path
        self.ssh = None

    def connect(self):
        # Create an SSH client
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, self.port, self.username, self.password)

    def run_script(self, project_name, run_number, pix_size, num_checks, seconds, user_id):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        # Check if the script exists on the remote server
        stdin, stdout, stderr = self.ssh.exec_command(f'ls -l {self.script_path}')
        file_check_output = stdout.read().decode('utf-8')
        file_check_error = stderr.read().decode('utf-8')

        print("File Check Output:")
        print(file_check_output)
        print("File Check Error:")
        print(file_check_error)

        if "No such file or directory" in file_check_error:
            raise Exception(f"The script path {self.script_path} does not exist on the remote server.")

        # Execute the shell script remotely
        stdin, stdout, stderr = self.ssh.exec_command(f'bash {self.script_path}')

        # Handle prompts sequentially
        stdin.write(f'{project_name}\n')
        stdin.flush()
        stdin.write(f'{run_number}\n')
        stdin.flush()
        stdin.write(f'{pix_size}\n')
        stdin.flush()
        stdin.write(f'{num_checks}\n')
        stdin.flush()
        stdin.write(f'{seconds}\n')
        stdin.flush()
        stdin.write(f'{user_id}\n')
        stdin.flush()

        # Read the output and error streams
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        return output, error

    def close(self):
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None

