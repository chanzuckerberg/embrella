"""
Django-Q2 async tasks for pipeline execution status monitoring.
"""

from django.utils import timezone
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


def poll_pipe_execution_status(pipe_execution_id):
    """
    Django-Q task to poll SLURM job status and update PipeExecution.

    This task is scheduled to run periodically (every 5 minutes) until
    the job completes. It updates the PipeExecution status field based
    on the SLURM job state.

    Args:
        pipe_execution_id (int): ID of the PipeExecution instance

    Returns:
        dict: Result with status and action taken
    """
    from django_q.models import Schedule

    from processes.models import PipeExecution

    try:
        pipe_exec = PipeExecution.objects.get(id=pipe_execution_id)

        # Get cluster_id from parameters (default to 'czii' for legacy jobs)
        from processes.services.cluster_resolver import cluster_id_from_parameters

        cluster_id = cluster_id_from_parameters(pipe_exec.parameters)
        if cluster_id == "czii" and "cluster_id" not in (pipe_exec.parameters or {}):
            logger.warning(
                f"PipeExecution {pipe_execution_id} has no cluster_id in parameters - "
                f"defaulting to 'czii' (legacy job)",
            )

        # Check if job is still active
        job_active = check_job_status(pipe_exec.job_id, cluster_id=cluster_id)

        if not job_active:
            # Job completed - update status and stop polling
            pipe_exec.status = "completed"
            pipe_exec.completed_at = timezone.now()
            pipe_exec.save(update_fields=["status", "completed_at"])

            # Cancel this scheduled task
            Schedule.objects.filter(
                func="processes.tasks.poll_pipe_execution_status",
                args=str(pipe_execution_id),
            ).delete()

            logger.info(
                f"PipeExecution {pipe_execution_id} completed. "
                f"Job {pipe_exec.job_id} is no longer active. Stopped polling.",
            )

            return {
                "success": True,
                "pipe_execution_id": pipe_execution_id,
                "action": "completed",
                "status": "completed",
                "message": "Job completed, polling stopped",
            }

        # Job still active - update status if needed
        if pipe_exec.status == "submitted":
            # First time we see it running
            pipe_exec.status = "running"
            pipe_exec.started_at = timezone.now()
            pipe_exec.save(update_fields=["status", "started_at"])

            logger.info(
                f"PipeExecution {pipe_execution_id} transitioned to running. Job {pipe_exec.job_id} is active.",
            )

            return {
                "success": True,
                "pipe_execution_id": pipe_execution_id,
                "action": "status_updated",
                "status": "running",
                "message": "Status updated to running",
            }

        # Job still running, no status change needed
        logger.debug(
            f"PipeExecution {pipe_execution_id} still running. Job {pipe_exec.job_id} is active.",
        )

        return {
            "success": True,
            "pipe_execution_id": pipe_execution_id,
            "action": "no_change",
            "status": pipe_exec.status,
            "message": "Job still running",
        }

    except PipeExecution.DoesNotExist:
        logger.error(f"PipeExecution {pipe_execution_id} does not exist")

        # Cancel scheduled task for non-existent execution
        Schedule.objects.filter(
            func="processes.tasks.poll_pipe_execution_status",
            args=str(pipe_execution_id),
        ).delete()

        return {
            "success": False,
            "pipe_execution_id": pipe_execution_id,
            "error": "PipeExecution not found",
        }

    except Exception as e:
        logger.error(
            f"Error polling status for PipeExecution {pipe_execution_id}: {str(e)}",
        )
        return {
            "success": False,
            "pipe_execution_id": pipe_execution_id,
            "error": str(e),
        }


def schedule_pipe_execution_monitoring(pipe_execution_id, job_id):
    """
    Start monitoring a PipeExecution via periodic Django-Q tasks.

    Schedules a task to run every 5 minutes that checks SLURM job status
    and updates the PipeExecution record. The task will automatically
    cancel itself when the job completes.

    Args:
        pipe_execution_id (int): ID of the PipeExecution instance
        job_id (str): SLURM job ID

    Returns:
        str: Django-Q schedule ID
    """
    from django_q.models import Schedule
    from django_q.tasks import schedule

    schedule_id = schedule(
        "processes.tasks.poll_pipe_execution_status",
        pipe_execution_id,
        schedule_type=Schedule.MINUTES,
        minutes=5,
        repeats=-1,  # Indefinitely until cancelled
        task_name=f"poll_pipe_exec_{pipe_execution_id}",
    )

    logger.info(
        f"Scheduled monitoring for PipeExecution {pipe_execution_id}, job {job_id}. Schedule ID: {schedule_id}",
    )

    return schedule_id
