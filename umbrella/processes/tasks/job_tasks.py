"""
Django-Q2 async tasks for pipeline execution status monitoring.
"""

from umbrella_logger import logger

from processes.tasks._setup import *  # noqa: F401,F403 - Django setup


def check_job_status(job_id, cluster_id):
    """
    Check if a SLURM job is still active on a specific cluster.

    Args:
        job_id (str): SLURM job ID
        cluster_id (str): Cluster to check ('czii' or 'bruno')

    Returns:
        bool: True if job is active (PENDING, RUNNING, etc.), False if completed/failed
    """
    from workflow.views.utils import track_jobs_internal

    active_states = ["PENDING", "CONFIGURING", "RUNNING", "COMPLETING"]

    try:
        jobs_data = track_jobs_internal(cluster_id=cluster_id)

        for job in jobs_data.get("jobs", []):
            # SLURM returns 'JOBID' key from squeue output
            slurm_job_id = str(job.get("JOBID") or job.get("job_id") or "")
            # Handle hetjob format: "9238+0" should match "9238"
            # Extract base job ID from hetjob format
            slurm_base_id = slurm_job_id.split("+")[0] if "+" in slurm_job_id else slurm_job_id
            target_base_id = str(job_id).split("+")[0] if "+" in str(job_id) else str(job_id)

            if slurm_base_id == target_base_id:
                state = job.get("ST", job.get("state", "")).upper()
                is_active = state in active_states
                logger.info(
                    f"Found job {job_id} (SLURM: {slurm_job_id}) on {cluster_id} cluster "
                    f"with state {state} (active={is_active})",
                )
                return is_active

    except Exception as e:
        logger.error(f"Error checking job status for {job_id} on {cluster_id}: {str(e)}")
        # Return False on error - assume job completed
        return False

    # Job not found on this cluster = completed or never existed
    logger.info(f"Job {job_id} not found on {cluster_id}, assuming completed")
    return False
