import paramiko

from umbrella_logger import logger
import subprocess
import os
from jinja2 import Environment, FileSystemLoader
from umbrella_logger import logger
import paramiko

class Aretomo3(object):
    def __init__(self, hostname, port, username, password, remote_script_dir, local_template_path):
        """
        :param hostname: Remote host to connect to.
        :param port: SSH port.
        :param username: SSH username.
        :param password: SSH password.
        :param remote_script_dir: Remote directory where job scripts are stored.
        :param local_template_path: Local file path to the Jinja2 template.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.remote_script_dir = remote_script_dir
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        # Create an SSH client
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, self.port, self.username, self.password)
        logger.info(f"Connected to {self.hostname}")

    def run_advanced_script(self, project_name, use_old_gain, run_number, pixel_size, dose_number, frame_dose, gain_file_name=None, denoise_training=None, use_advanced_params=None, tilt_axis=None, tilt_axis_refine=None, align_z=None, vol_z=None, imod_option=None, local_shift=None, tilt_offset=None, thickness_mesaure=None, user_id=None):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        try:
            # Log input parameters
            logger.info(f"Input Parameters: project_name={project_name}, use_old_gain={use_old_gain}, run_number={run_number}, pixel_size={pixel_size}, dose_number={dose_number}, frame_dose={frame_dose}, gain_file_name={gain_file_name}, denoise_training={denoise_training}, use_advanced_params={use_advanced_params}, tilt_axis={tilt_axis}, tilt_axis_refine={tilt_axis_refine}, align_z={align_z}, vol_z={vol_z}, imod_option={imod_option}, local_shift={local_shift}, tilt_offset={tilt_offset}, thickness_mesaure={thickness_mesaure}")

            # Validate required parameters
            if not all([project_name, use_old_gain, run_number, pixel_size, dose_number]):
                missing_params = []
                if not project_name: missing_params.append("project_name")
                if not use_old_gain: missing_params.append("use_old_gain")
                if not run_number: missing_params.append("run_number")
                if not pixel_size: missing_params.append("pixel_size")
                if not dose_number: missing_params.append("dose_number")
                raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

            # Set up the Jinja2 environment using the directory of the template
            try:
                template_dir = os.path.dirname(self.local_template_path)
                template_file = os.path.basename(self.local_template_path)
                logger.info(f"Loading template from: {template_dir}/{template_file}")
                
                if not os.path.exists(self.local_template_path):
                    raise FileNotFoundError(f"Template file not found: {self.local_template_path}")
                
                env = Environment(loader=FileSystemLoader(template_dir))
                template = env.get_template(template_file)
            except Exception as e:
                logger.error(f"Error setting up Jinja2 environment: {str(e)}")
                raise

            # Calculate binning values
            try:
                tomo_bin_5A = round(5 / float(pixel_size), 2)
                tomo_bin_10A = round(10 / float(pixel_size), 2)
                logger.info(f"Calculated binning values: tomo_bin_5A={tomo_bin_5A}, tomo_bin_10A={tomo_bin_10A}")
            except Exception as e:
                logger.error(f"Error calculating binning values: {str(e)}")
                raise

            # Render the template with the provided parameters
            try:
                rendered_script = template.render(
                    project_name=project_name,
                    use_old_gain=use_old_gain,
                    run_number=run_number,
                    pixel_size=pixel_size,
                    dose_number=dose_number,
                    frame_dose=frame_dose if frame_dose and frame_dose.lower() != 'none' else '',
                    gain_file_name=gain_file_name,
                    denoise_training=denoise_training,
                    use_advanced_params=use_advanced_params,
                    tilt_axis=tilt_axis,
                    tilt_axis_refine=tilt_axis_refine,
                    align_z=align_z,
                    vol_z=vol_z,
                    imod_option=imod_option,
                    local_shift=local_shift,
                    tilt_offset=tilt_offset,
                    thickness_mesaure=thickness_mesaure,
                    user_id=user_id,
                    tomo_bin_5A=tomo_bin_5A,
                    tomo_bin_10A=tomo_bin_10A
                )
                logger.info(f"Successfully rendered template for project {project_name}")
            except Exception as e:
                logger.error(f"Error rendering template: {str(e)}")
                raise

            # Define the remote file name and path
            remote_script_filename = f"{project_name}_aretomo3_advanced.sh"
            remote_script_path = os.path.join(self.remote_script_dir, remote_script_filename)
            logger.info(f"Remote script path: {remote_script_path}")

            # Upload the rendered script using SFTP
            try:
                sftp = self.ssh.open_sftp()
                try:
                    sftp.stat(remote_script_path)  # Check if file exists
                    sftp.remove(remote_script_path)  # Remove it if it does
                    logger.info(f"Removed existing script file: {remote_script_path}")
                except FileNotFoundError:
                    logger.info(f"No existing script file found at {remote_script_path}")

                with sftp.file(remote_script_path, "w") as remote_file:
                    remote_file.write(rendered_script)
                sftp.chmod(remote_script_path, 0o755)
                sftp.close()
                logger.info(f"Successfully uploaded rendered script to {remote_script_path}")
            except Exception as e:
                logger.error(f"Error during SFTP operations: {str(e)}")
                raise

            # Submit the job using sbatch
            try:
                submit_cmd = f"cd {self.remote_script_dir} && sbatch {remote_script_filename}"
                logger.info(f"Executing command: {submit_cmd}")
                stdin, stdout, stderr = self.ssh.exec_command(submit_cmd)
                submit_output = stdout.read().decode('utf-8')
                submit_error = stderr.read().decode('utf-8')

                logger.info(f"Submission Output: {submit_output}")
                if submit_error:
                    logger.error(f"Submission Error: {submit_error}")
                    raise Exception(f"Job submission failed: {submit_error}")

                return submit_output, submit_error
            except Exception as e:
                logger.error(f"Error during job submission: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error during AreTomo3 job submission: {str(e)}")
            raise

    def close(self):
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None
            logger.info("SSH connection closed.")

    def run_script(self, project_name, run_number, pix_size, total_dose, fm_dose, user_id):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")

        # Check if the script exists on the remote server
        stdin, stdout, stderr = self.ssh.exec_command(f'ls -l {self.local_template_path}')
        file_check_output = stdout.read().decode('utf-8')
        file_check_error = stderr.read().decode('utf-8')

        logger.info(f"File Check Output: {file_check_output}")
        logger.info(f"File Check Error: {file_check_error}")


        if "No such file or directory" in file_check_error:
            raise Exception(f"The script path {self.local_template_path} does not exist on the remote server.")

        # Execute the shell script remotely
        stdin, stdout, stderr = self.ssh.exec_command(f'bash {self.local_template_path}')

        # Handle prompts sequentially
        stdin.write(f'{project_name}\n')
        stdin.flush()
        stdin.write(f'{run_number}\n')
        stdin.flush()
        stdin.write(f'{pix_size}\n')
        stdin.flush()
        stdin.write(f'{total_dose}\n')
        stdin.flush()
        stdin.write(f'{fm_dose}\n')
        stdin.flush()
        stdin.write(f'{user_id}\n')
        stdin.flush()

        # Read the output and error streams
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        return output, error

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




class Denoiset(object):
    def __init__(self, hostname, port, username, password, remote_script_dir, local_template_path):
        """
        :param hostname: Remote host to connect to.
        :param port: SSH port.
        :param username: SSH username.
        :param password: SSH password.
        :param remote_script_dir: Remote directory where job scripts are stored.
        :param local_template_path: Local file path to the Jinja2 template (e.g., 'denoiset_template.sh').
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.remote_script_dir = remote_script_dir  # e.g. "/hpc/projects/group.czii/krios1.processing/denoise/scripts"
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        # Establish an SSH connection.
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, self.port, self.username, self.password)
        logger.info(f"Connected to {self.hostname}")

    def run_script(self, session_name, run_number, denoise_run_number, model_name, user_id=None, live_denoising=False):
        """
        Loads an external Jinja2 template, renders it with the provided parameters,
        uploads the rendered script to the remote server, and submits it via sbatch.
        
        :param session_name: The session identifier (e.g., "24aug30a")
        :param run_number: The run number (e.g., "run001") to be used for both aretomo_run and denoise_run.
        :param model_name: The model name (e.g., "lysosome.pth")
        :param user_id: Optional user id (not used in the template above)
        :param live_denoising: Flag to indicate if live denoising should be enabled.
        :return: Submission output and error messages.
        """
        try:
            # Set up the Jinja2 environment using the directory of the template.
            template_dir = os.path.dirname(self.local_template_path)
            template_file = os.path.basename(self.local_template_path)
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_file)
            # Render the template with the provided parameters.
            rendered_script = template.render(
                session=session_name,
                aretomo_run=run_number,
                denoise_run=denoise_run_number,  # Adjust if denoise_run should be different.
                model_name=model_name,
                live_denoising=live_denoising
            )
            logger.info(f"Rendered script for session {session_name}:\n{rendered_script}")
            # Define the remote file name and full path.
            remote_script_filename = f"{session_name}_predict3d.sh"
            remote_script_path = os.path.join(self.remote_script_dir, remote_script_filename)
            
            # Upload the rendered script to the remote server using SFTP.
            sftp = self.ssh.open_sftp()

            # --- NEW LOGIC: Remove existing file if it exists ---
            try:
                sftp.stat(remote_script_path)  # Check if file exists
                sftp.remove(remote_script_path) # Remove it if it does
                logger.info(f"Removed existing script file: {remote_script_path}")
            except FileNotFoundError:
                # This just means the file doesn't exist—safe to ignore
                pass

            with sftp.file(remote_script_path, "w") as remote_file:
                remote_file.write(rendered_script)
            sftp.chmod(remote_script_path, 0o755)
            sftp.close()
            logger.info(f"Uploaded rendered script to {remote_script_path}")

            # Submit the job using sbatch.
            submit_cmd = f"cd {self.remote_script_dir} && sbatch {remote_script_filename}"
            stdin, stdout, stderr = self.ssh.exec_command(submit_cmd)
            submit_output = stdout.read().decode('utf-8')
            submit_error = stderr.read().decode('utf-8')

            logger.info(f"Submission Output: {submit_output}")
            if submit_error:
                logger.error(f"Submission Error: {submit_error}")

            return submit_output, submit_error
        except Exception as e:
            logger.error(f"Error during Denoiset job submission: {e}")
            raise

    def close(self):
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None
            logger.info("SSH connection closed.")


class StatusChecker(object):
    def __init__(self, hostname, port, username, password, remote_script_dir, local_template_path):
        """
        :param hostname: Remote host to connect to.
        :param port: SSH port.
        :param username: SSH username.
        :param password: SSH password.
        :param remote_script_dir: Remote directory where the status-check script will be stored.
        :param local_template_path: Local path to the Jinja2 template for the status-check script.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.remote_script_dir = remote_script_dir
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        """
        Establish an SSH connection to the remote server.
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, self.port, self.username, self.password)
        logger.info(f"Connected to {self.hostname}")

    def check_status(self, session_name, live_denoising=False):
        """
        Loads a Jinja2-based status-check script, renders it with the given parameters,
        uploads it to the remote server, and then executes it with 'bash'.
        
        :param session_name: The session identifier (e.g., "24aug30a")
        :return: (script_output, script_error) as a tuple of strings
        """
        try:
            # 1) Prepare the Jinja2 environment
            template_dir = os.path.dirname(self.local_template_path)
            template_file = os.path.basename(self.local_template_path)
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_file)

            # 2) Render the template
            rendered_script = template.render(
                session=session_name,
            )
            logger.info(f"Rendered script for session '{session_name}':\n{rendered_script}")

            # 3) Define the remote file name and path
            remote_script_filename = f"{session_name}_status_check.sh"
            remote_script_path = os.path.join(self.remote_script_dir, remote_script_filename)

            # 4) Use SFTP to upload the script (removing any existing version)
            sftp = self.ssh.open_sftp()
            try:
                sftp.stat(remote_script_path)  # Check if file exists
                sftp.remove(remote_script_path)
                logger.info(f"Removed existing file: {remote_script_path}")
            except FileNotFoundError:
                pass  # It's fine if the file doesn't exist yet

            with sftp.file(remote_script_path, "w") as remote_file:
                remote_file.write(rendered_script)

            # Make the remote script executable
            sftp.chmod(remote_script_path, 0o755)
            sftp.close()
            logger.info(f"Uploaded rendered script to: {remote_script_path}")

            # 5) Execute the script using bash
            check_cmd = f"cd {self.remote_script_dir} && bash {remote_script_filename} {session_name}"
            stdin, stdout, stderr = self.ssh.exec_command(check_cmd)

            script_output = stdout.read().decode('utf-8', errors='replace')
            script_error = stderr.read().decode('utf-8', errors='replace')

            # Log results
            if script_output.strip():
                logger.info(f"Status check output:\n{script_output}")
            if script_error.strip():
                logger.error(f"Status check error:\n{script_error}")

            return script_output, script_error

        except Exception as e:
            logger.error(f"Error during status check: {e}")
            raise

    def close(self):
        """
        Close the SSH connection.
        """
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None
            logger.info("SSH connection closed.")