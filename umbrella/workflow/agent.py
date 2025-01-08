import paramiko

from umbrella_logger import logger
import subprocess

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


    def run_advanced_script(
            self,
            project_name,
            run_number,
            pix_size,
            total_dose,
            num_checks,
            use_old_gain,
            gain_file_name=None,
            denoise_training=None,
            even_odd_split=None,
            use_advanced_params=None,
            tilt_axis=-1,
            align_z=-1,
            vol_z=-1
        ):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        # Verify if the script exists on the remote server
        try:
            stdin, stdout, stderr = self.ssh.exec_command(f'ls -l {self.script_path}')
            file_check_output = stdout.read().decode('utf-8')
            file_check_error = stderr.read().decode('utf-8')

            logger.info(f"File Check Output: {file_check_output}")
            logger.info(f"File Check Error: {file_check_error}")

            if "No such file or directory" in file_check_error:
                raise FileNotFoundError(f"The script path {self.script_path} does not exist on the remote server.")
        except Exception as e:
            logger.error(f"Error checking script existence: {e}")
            raise

        # Execute the advanced shell script remotely
        try:
            stdin, stdout, stderr = self.ssh.exec_command(f'bash {self.script_path}')
        except Exception as e:
            logger.error(f"Error executing the script: {e}")
            raise

        def write_input(value):
            """Helper function to write input to the script."""
            stdin.write(f'{value}\n')
            stdin.flush()

        try:
            # Mandatory initial input
            write_input(project_name)
            write_input(use_old_gain)

            if use_old_gain.lower() == 'yes':
                if not gain_file_name:
                    raise ValueError("gain_file_name must be provided when use_old_gain is 'yes'.")
                write_input(gain_file_name)

            # Common inputs regardless of use_old_gain
            write_input(run_number)
            write_input(denoise_training)
            write_input(even_odd_split)
            write_input(pix_size)

            if use_advanced_params and use_advanced_params.lower() == 'yes':
                write_input(use_advanced_params)
                write_input(tilt_axis)
                write_input(align_z)
                write_input(vol_z)
            elif use_advanced_params and use_advanced_params.lower() == 'no':
                write_input(use_advanced_params)

            write_input(total_dose)
            write_input(num_checks)

        except Exception as e:
            logger.error(f"Error during input writing: {e}")
            raise

        # Read the output and error streams
        try:
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            if stderr.channel.recv_exit_status() != 0:
                logger.error(f"Script execution failed with error: {error}")
                raise subprocess.CalledProcessError(stderr.channel.recv_exit_status(), self.script_path, output, error)

            logger.info(f"Script Output: {output}")
            return output, error
        except Exception as e:
            logger.error(f"Error reading script output: {e}")
            raise

    def run_script(self, project_name, run_number, pix_size, total_dose, num_checks, user_id):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        # Check if the script exists on the remote server
        stdin, stdout, stderr = self.ssh.exec_command(f'ls -l {self.script_path}')
        file_check_output = stdout.read().decode('utf-8')
        file_check_error = stderr.read().decode('utf-8')

        logger.info(f"File Check Output: {file_check_output}")
        logger.info(f"File Check Error: {file_check_error}")


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
        stdin.write(f'{total_dose}\n')
        stdin.flush()
        stdin.write(f'{num_checks}\n')
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

    def cancel(self, job_number):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        # Execute the scancel command with the given job number
        stdin, stdout, stderr = self.ssh.exec_command(f'scancel {job_number}')

        # Read the output and error streams
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if error:
            logger.error(f"Cancel Error: {error}")

        return output, error

    def track_jobs(self, job_name, all=False):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")
        if all and job_name is None:
            stdin, stdout, stderr = self.ssh.exec_command(f'squeue')
        else:
            # Execute the squeue command
            stdin, stdout, stderr = self.ssh.exec_command(f'squeue -n {job_name}')

        # Read the output and error streams
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if error:
            logger.error(f"Track Jobs Error: {error}")

        return output, error
