import os

from jinja2 import Environment, FileSystemLoader
from umbrella_logger import logger

from common import clusterio


class Aretomo3(object):
    def __init__(self, cluster_id, auth, remote_script_dir, local_template_path):
        """
        :param cluster_id: Cluster to use
        :param auth: Cluster credentials.
        :param remote_script_dir: Remote directory where job scripts are stored.
        :param local_template_path: Local file path to the Jinja2 template.
        """
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        # Create an SSH client
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)
        logger.info(f"Connected to {self.cluster_id}")

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
                    tomo_bin_10A=tomo_bin_10A,
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

    def run_script(self, project_name, run_number, pix_size, total_dose, frame_dose, user_id):
        """Execute the AreTomo3 script using a Jinja2 template."""
        try:
            logger.info(f"Running AreTomo3 script for project {project_name}")
            logger.info(f"Input parameters: run_number={run_number}, pix_size={pix_size}, total_dose={total_dose}, frame_dose={frame_dose}")

            # Set up Jinja2 environment
            env = Environment(loader=FileSystemLoader(os.path.dirname(self.local_template_path)))
            template = env.get_template(os.path.basename(self.local_template_path))

            # Calculate binning values
            tomo_bin_5A = round(5 / float(pix_size), 2)
            tomo_bin_10A = round(10 / float(pix_size), 2)

            # Render the template with parameters
            rendered_script = template.render(
                project_name=project_name,
                run_number=run_number,
                pix_size=pix_size,
                total_dose=total_dose,
                frame_dose=frame_dose,
                tomo_bin_5A=tomo_bin_5A,
                tomo_bin_10A=tomo_bin_10A,
                user_id=user_id,
            )

            # Upload the rendered script to the remote server
            remote_script_path = f"{self.remote_script_dir}/run_aretomo3_basic_{project_name}_{run_number}.sh"
            with self.ssh.open_sftp().file(remote_script_path, 'w') as f:
                f.write(rendered_script)

            # Make the script executable
            self.ssh.exec_command(f'chmod 755 {remote_script_path}')

            # Submit the job using sbatch
            stdin, stdout, stderr = self.ssh.exec_command(f'sbatch {remote_script_path}')
            output = stdout.read().decode()
            error = stderr.read().decode()

            if error:
                logger.error(f"Error submitting AreTomo3 job: {error}")
            else:
                logger.info(f"AreTomo3 job submitted successfully: {output}")

            return output, error

        except Exception as e:
            error_msg = f"Error in run_script: {str(e)}"
            logger.error(error_msg)
            return "", error_msg



class Denoiset(object):
    def __init__(self, cluster_id, auth, remote_script_dir, local_template_path):
        """
        :param cluster_id: Cluster to use.
        :param auth: Cluster credentials.
        :param remote_script_dir: Remote directory where job scripts are stored.
        :param local_template_path: Local file path to the Jinja2 template (e.g., 'denoiset_template.sh').
        """
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir  # e.g. "/hpc/projects/group.czii/krios1.processing/denoise/scripts"
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        # Establish an SSH connection.
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)
        logger.info(f"Connected to {self.cluster_id}")

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
                live_denoising=live_denoising,
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
    def __init__(self, cluster_id, auth, remote_script_dir, local_template_path):
        """
        :param cluster_id: Cluster to use
        :param auth: Cluster credentials.
        :param remote_script_dir: Remote directory where the status-check script will be stored.
        :param local_template_path: Local path to the Jinja2 template for the status-check script.
        """
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir
        self.local_template_path = local_template_path
        self.ssh = None

    def connect(self):
        """
        Establish an SSH connection to the remote server.
        """
        self.auth["username"] = os.getenv("SLURM_USER") # force to be service user
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)
        logger.info(f"Connected to {self.cluster_id}")

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

    def track_jobs(self, job_name, all=False):
        if self.ssh is None:
            raise Exception("SSH connection not established. Call connect() first.")
        # Use pipe delimiter for reliable parsing, even when fields contain spaces
        # Use %T (extended state) instead of %t (compact state) to get full state names like "PENDING" instead of "PD"
        # This ensures proper mapping in SLURM_STATE_TO_LABEL

        # Build squeue command with format options
        # %i=jobid, %P=partition, %j=name, %u=user, %T=state (extended), %M=time, %L=timeleft, %D=nodes, %R=reason
        if all and job_name is None:
            squeue_cmd = 'echo "JOBID|PARTITION|NAME|USER|ST|TIME|TIMELEFT|NODES|NODELIST(REASON)"; squeue --noheader -o "%i|%P|%j|%u|%T|%M|%L|%D|%R"'
        else:
            # Execute the squeue command with job name filter
            squeue_cmd = f'echo "JOBID|PARTITION|NAME|USER|ST|TIME|TIMELEFT|NODES|NODELIST(REASON)"; squeue --noheader -o "%i|%P|%j|%u|%T|%M|%L|%D|%R" -n {job_name}'

        stdin, stdout, stderr = self.ssh.exec_command(squeue_cmd)

        # Read the output and error streams
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if error:
            logger.error(f"Track Jobs Error: {error}")

        return output, error

    def close(self):
        """
        Close the SSH connection.
        """
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None
            logger.info("SSH connection closed.")

# A generic class to submit remote jobs using a Jinja2 template

class RemoteJobSubmitter:
    def __init__(self, cluster_id, auth, remote_script_dir):
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir
        self.ssh = None

    def connect(self):
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)

    def run_script(self, template_path: str, job_name: str, **kwargs):
        if template_path is None and 'script_content' in kwargs:
            rendered = kwargs['script_content']
        else:
            # Render any Jinja template with arbitrary parameters
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            rendered = template.render(**kwargs)

        # Upload to remote
        remote_script = os.path.join(self.remote_script_dir, f"{job_name}.sh")
        sftp = self.ssh.open_sftp()
        try:
            # Ensure remote directory exists
            try:
                sftp.stat(self.remote_script_dir)
            except FileNotFoundError:
                # Directory doesn't exist, create it (and any parent directories)
                parent_dirs = []
                current_path = self.remote_script_dir
                while current_path and current_path != '/':
                    try:
                        sftp.stat(current_path)
                        break  # This directory exists, stop
                    except FileNotFoundError:
                        parent_dirs.insert(0, current_path)
                        current_path = os.path.dirname(current_path)

                # Create all missing directories
                for dir_path in parent_dirs:
                    sftp.mkdir(dir_path)

            with sftp.file(remote_script, "w") as f:
                f.write(rendered)
            sftp.chmod(remote_script, 0o755)
        finally:
            sftp.close()

        # Submit via sbatch (for scripts with #SBATCH directives)
        cmd = f"cd {self.remote_script_dir} && sbatch {job_name}.sh"
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        return stdout.read().decode(), stderr.read().decode()

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

        return output == '' and error == '', error

    def close(self):
        if self.ssh:
            self.ssh.close()
            self.ssh = None


