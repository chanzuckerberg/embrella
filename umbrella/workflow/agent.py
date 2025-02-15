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
        use_old_gain,
        run_number,
        pixel_size,
        dose_number,
        num_checks,
        denoise_training=None,
        even_odd_split=None,
        use_advanced_params=None,
        tilt_axis=None,
        tilt_axis_refine=None,
        align_z=None,
        vol_z=None,
        imod_option=None,
        user_id=None,
        local_shift=None,
        tilt_offset=None,
        thickness_mesaure=None,
        gain_file_name=None,
    ):
        """
        An updated method signature that aligns more closely with the parameters
        parsed in run_aretomo3_advanced. Modify and/or rename these parameters as
        needed to match your actual shell-script inputs.
        """
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        try:
            # Log input parameters
            logger.info(f"Input Parameters: project_name={project_name}, use_old_gain={use_old_gain}, "
                        f"run_number={run_number}, pixel_size={pixel_size}, dose_number={dose_number}, "
                        f"num_checks={num_checks}, gain_file_name={gain_file_name}, denoise_training={denoise_training}, "
                        f"use_advanced_params={use_advanced_params}, tilt_axis={tilt_axis}, "
                        f"tilt_axis_refine={tilt_axis_refine}, align_z={align_z}, vol_z={vol_z}, imod_option={imod_option}, "
                        f"local_shift={local_shift}, tilt_offset={tilt_offset}, thickness_mesaure={thickness_mesaure}")

            # Check if the script exists on the remote server
            stdin, stdout, stderr = self.ssh.exec_command(f'ls -l {self.script_path}', timeout=10)
            file_check_output = stdout.read().decode('utf-8')
            file_check_error = stderr.read().decode('utf-8')
            logger.info(f"File Check Output: {file_check_output}")
            if "No such file or directory" in file_check_error:
                raise FileNotFoundError(f"The script path {self.script_path} does not exist on the remote server.")
        except Exception as e:
            logger.error(f"Error checking script existence: {e}")
            raise

        try:
            # Execute the script
            stdin, stdout, stderr = self.ssh.exec_command(f'bash {self.script_path}', timeout=120)
        except Exception as e:
            logger.error(f"Error executing the script: {e}")
            raise

        # Helper function for writing to stdin
        def write_input(value):
            """Helper function to write a single line of input to the script."""
            stdin.write(f'{value}\n')
            stdin.flush()
            logger.debug(f"Written to script: {value}")

        try:
            # Provide inputs to the script in the order it expects
            write_input(project_name)
            write_input(use_old_gain)

            if use_old_gain.lower() == 'yes':
                if not gain_file_name:
                    raise ValueError("gain_file_name must be provided when use_old_gain is 'yes'.")
                write_input(gain_file_name)

            write_input(run_number)
            write_input(denoise_training)
            write_input(even_odd_split)
            logger.info("denoise training:{}".format(denoise_training))
            logger.info("denoise training:{}".format(denoise_training))
            write_input(pixel_size)

            if use_advanced_params.lower() == 'yes':
                write_input(use_advanced_params)
                write_input(tilt_axis or "")
                write_input(tilt_axis_refine or "")
                write_input(align_z or "")
                write_input(vol_z or "")
                write_input(imod_option or "")
                write_input(local_shift or "")
                write_input(tilt_offset or "")
                write_input(thickness_mesaure or "")
            elif use_advanced_params.lower() == 'no':
                write_input(use_advanced_params)

            write_input(dose_number)
            write_input(num_checks)
            write_input(user_id) #automatically handling by script - this is for user_id

            # Close stdin after writing all inputs
            stdin.close()

            # Read script output and errors
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            logger.info(f"Script Output: {output}")
            logger.error(f"Script Error: {error}")

            # Log both output and error for debugging purposes
            logger.info(f"Full Script Response:\nOutput:\n{output}\nError:\n{error}")

            # Check exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                logger.error(f"Script execution failed with error: {error}")
                raise subprocess.CalledProcessError(
                    exit_status, self.script_path, output=output, stderr=error
                )

            return output, error
        except Exception as e:
            logger.error(f"Error during script execution: {e}")
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
