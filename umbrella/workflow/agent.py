import os

from umbrella_logger import logger

from common import clusterio


class StatusChecker(object):
    def __init__(self, cluster_id, auth):
        """
        :param cluster_id: Cluster to use
        :param auth: Cluster credentials.
        """
        self.cluster_id = cluster_id
        self.auth = auth
        self.ssh = None

    def connect(self):
        """
        Establish an SSH connection to the remote server.
        """
        self.auth["username"] = os.getenv("SLURM_USER")  # force to be service user
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)
        logger.info(f"Connected to {self.cluster_id}")

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
        output = stdout.read().decode("utf-8")
        error = stderr.read().decode("utf-8")

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


# Uploads a rendered SLURM script and submits it with sbatch


class RemoteJobSubmitter:
    def __init__(self, cluster_id, auth, remote_script_dir=None):
        # remote_script_dir is only needed by run_script(); cancel() works without it.
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir
        self.ssh = None
        self.last_script_path = None

    def connect(self):
        self.ssh = clusterio.get_cluster_ssh_connection(cluster_id=self.cluster_id, auth=self.auth)

    def run_script(self, script_content: str, job_name: str):
        """Upload `script_content` as `{job_name}.sh` and sbatch it. Returns (stdout, stderr)."""
        remote_script = os.path.join(self.remote_script_dir, f"{job_name}.sh")
        self.last_script_path = remote_script
        sftp = self.ssh.open_sftp()
        try:
            # Ensure remote directory exists
            try:
                sftp.stat(self.remote_script_dir)
            except FileNotFoundError:
                # Directory doesn't exist, create it (and any parent directories)
                parent_dirs = []
                current_path = self.remote_script_dir
                while current_path and current_path != "/":
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
                f.write(script_content)
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
        stdin, stdout, stderr = self.ssh.exec_command(f"scancel {job_number}")

        # Read the output and error streams
        output = stdout.read().decode("utf-8")
        error = stderr.read().decode("utf-8")

        if error:
            logger.error(f"Cancel Error: {error}")

        return output == "" and error == "", error

    def close(self):
        if self.ssh:
            self.ssh.close()
            self.ssh = None
