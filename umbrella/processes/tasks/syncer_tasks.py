"""
Django-Q2 async tasks for output file syncer monitoring.
"""
# isort: skip_file
# _setup must be imported first to call django.setup() before any Django imports

from processes.tasks._setup import *  # noqa: F401,F403

from datetime import timedelta

from django.utils import timezone
from django_q.tasks import async_task
from umbrella_logger import logger

from processes.tasks.job_tasks import check_job_status

OUTPUT_SYNC_INTERVAL = timedelta(minutes=5)
SACCT_POLL_INTERVAL = timedelta(seconds=60)
SACCT_NOT_YET_LISTED_DELAY = timedelta(seconds=30)
SACCT_ERROR_BACKOFF = timedelta(seconds=120)


def _run_later(func, args, name, delay, timeout=None, hook=""):
    # Django-Q2 has no per-task eta; a plain async_task would run again
    # immediately. A one-shot Schedule fires once at next_run, then deletes itself.
    from django_q.models import Schedule

    kwargs = {"task_name": name}
    if timeout:
        kwargs["timeout"] = timeout

    Schedule.objects.filter(name=name).delete()
    Schedule.objects.create(
        name=name,
        func=func,
        args=repr(args),
        kwargs=repr(kwargs),
        hook=hook,
        schedule_type=Schedule.ONCE,
        next_run=timezone.now() + delay,
    )


def run_syncer_iteration(syncer_class_path, base_path, session_name, run_id, job_id):
    """
    Django-Q task to run one iteration of a syncer and reschedule itself.

    This task instantiates a syncer, runs sync_results() once, checks if the
    SLURM job is still running, and reschedules itself if needed. It will
    stop rescheduling when the job completes or after max failures.

    Args:
        syncer_class_path (str): Full import path to syncer class
            (e.g., 'workflow.processors.aretomo3.syncer.AretomoSyncer')
        base_path (str): Base path for syncer (e.g., '/hpc/projects/krios1.processing/aretomo3')
        session_name (str): TEM session name
        run_id (str): Run ID (e.g., 'run001')
        job_id (str): SLURM job ID to monitor

    Returns:
        dict: Result with status and action taken
    """
    from tem.models import MsiSession

    from processes.models import PipeExecution

    try:
        # Import syncer class dynamically
        module_path, class_name = syncer_class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        syncer_class = getattr(module, class_name)

        # Determine cluster_id from the job's PipeExecution
        pipe_exec = PipeExecution.objects.filter(job_id=job_id).first()
        if not pipe_exec:
            logger.error(f"No PipeExecution found for job {job_id} - cannot determine cluster")
            return {
                "success": False,
                "action": "error",
                "message": "PipeExecution not found",
                "session": session_name,
                "run_id": run_id,
                "job_id": job_id,
            }

        # cluster_id is persisted in the parameters JSON field (default to 'czii' for legacy jobs)
        from processes.services.cluster_resolver import cluster_id_from_parameters

        cluster_id = cluster_id_from_parameters(pipe_exec.parameters)
        if cluster_id == "czii" and "cluster_id" not in (pipe_exec.parameters or {}):
            logger.warning(
                f"Job {job_id} has no cluster_id in parameters - defaulting to 'czii' (legacy job)",
            )

        logger.info(f"Job {job_id} uses cluster: {cluster_id}")

        # Check if job is still active
        job_active = check_job_status(job_id, cluster_id=cluster_id)

        if not job_active:
            logger.info(
                f"Job {job_id} is no longer running. Stopping syncer for {session_name}/{run_id}.",
            )
            # Log syncer completion to database
            from processes.models import SyncerLog, SyncerProcess

            SyncerLog.objects.create(
                pipe_execution=pipe_exec,
                job_id=job_id,
                action_type="stopped",
                message=f"Syncer stopped - job {job_id} completed",
                metadata={"reason": "job_completed", "cluster_id": cluster_id},
                session_name=session_name,
                run_id=run_id,
            )
            # Update SyncerProcess status
            SyncerProcess.objects.filter(job_id=job_id).update(
                status="completed",
                stopped_at=timezone.now(),
            )
            # Clean up transient logs now that syncer is complete
            from workflow.syncers import cleanup_transient_syncer_logs

            cleanup = cleanup_transient_syncer_logs(job_id)
            return {
                "success": True,
                "action": "stopped",
                "message": f"Job completed, syncer stopped. Removed {cleanup['deleted_count']} transient syncer logs for job {job_id}",
                "session": session_name,
                "run_id": run_id,
                "job_id": job_id,
            }

        # Verify session exists
        session = MsiSession.objects.filter(name=session_name).first()
        if not session:
            logger.error(f"Session {session_name} not found")
            return {
                "success": False,
                "error": "Session not found",
                "session": session_name,
            }

        # Instantiate syncer and run one iteration
        syncer = syncer_class(base_path=base_path, log_dir="/tmp")  # log_dir not used in task mode
        syncer.job_id = job_id  # Set job_id before setup so it's available for logging

        # Setup syncer with session and run info (creates initial log entry and SyncerProcess record)
        syncer.setup(run_id=run_id, session_name=session_name, cluster_id=cluster_id)

        # Run one sync iteration
        logger.info(f"Running syncer iteration for {session_name}/{run_id}")
        syncer.sync_results()

        # Schedule next iteration (5 minutes from now)
        _run_later(
            "processes.tasks.run_syncer_iteration",
            (syncer_class_path, base_path, session_name, run_id, job_id),
            name=f"syncer_{session_name}_{run_id}",
            delay=OUTPUT_SYNC_INTERVAL,
            timeout=300,  # 5 minute timeout
            hook="django_q.hooks.default",  # Use default hook for error handling
        )

        logger.info(f"Syncer iteration completed for {session_name}/{run_id}. Next run in 5 minutes.")

        return {
            "success": True,
            "action": "synced_and_rescheduled",
            "message": "Sync completed, next iteration scheduled",
            "session": session_name,
            "run_id": run_id,
            "job_id": job_id,
        }

    except Exception as e:
        logger.error(
            f"Error in syncer iteration for {session_name}/{run_id}: {str(e)}",
            exc_info=True,
        )
        # Log error to database
        try:
            from processes.models import SyncerLog, SyncerProcess

            SyncerLog.objects.create(
                job_id=job_id,
                action_type="error",
                message=f"Syncer error: {str(e)}",
                metadata={"error": str(e), "session_name": session_name, "run_id": run_id},
                session_name=session_name,
                run_id=run_id,
            )
            # Update SyncerProcess status to failed
            SyncerProcess.objects.filter(job_id=job_id).update(
                status="failed",
                stopped_at=timezone.now(),
                error_message=str(e),
            )
        except Exception as log_error:
            logger.warning(f"Failed to log syncer error to database: {log_error}")

        return {
            "success": False,
            "error": str(e),
            "session": session_name,
            "run_id": run_id,
            "job_id": job_id,
        }


def start_syncer_monitoring(syncer_class_path, base_path, session_name, run_id, job_id):
    """
    Start monitoring output files via a self-rescheduling syncer task.

    Creates an async task that will run every 5 minutes, checking remote
    filesystem for output files and creating ReviewTomogram records. The
    task will automatically stop when the SLURM job completes.

    Args:
        syncer_class_path (str): Full import path to syncer class
        base_path (str): Base path for syncer
        session_name (str): TEM session name
        run_id (str): Run ID
        job_id (str): SLURM job ID

    Returns:
        str: Django-Q task ID
    """
    task_id = async_task(
        "processes.tasks.run_syncer_iteration",
        syncer_class_path,
        base_path,
        session_name,
        run_id,
        job_id,
        task_name=f"syncer_{session_name}_{run_id}",
        timeout=300,  # 5 minute timeout
    )

    logger.info(
        f"Started syncer monitoring for {session_name}/{run_id}, job {job_id}. Task ID: {task_id}",
    )

    return task_id


def run_job_status_syncer(job_id: str, cluster_id: str = "czii"):
    """
    Single iteration of job status syncer.

    Queries SLURM's sacct for accurate job timing and status, updates
    the PipeExecution record, and self-reschedules until job reaches
    a terminal state.

    This is a lightweight syncer that runs for ALL jobs to ensure accurate
    completion timestamps, unlike the file-scanning syncers which are
    processor-specific.

    Args:
        job_id: SLURM job ID to track
        cluster_id: Cluster to query (czii or bruno)

    Returns:
        dict with status and job_id
    """
    from workflow.syncers import JobStatusSyncer

    syncer = JobStatusSyncer(job_id=job_id, cluster_id=cluster_id)
    syncer.setup()

    try:
        job_info = syncer.get_job_info_from_sacct()

        if job_info is None:
            # Job not in sacct yet (just submitted) - reschedule in 30 seconds
            logger.debug(f"Job {job_id} not in sacct yet, rescheduling...")
            _run_later(
                "processes.tasks.run_job_status_syncer",
                (job_id, cluster_id),
                name=f"job_status_{job_id}",
                delay=SACCT_NOT_YET_LISTED_DELAY,
            )
            return {"status": "waiting", "job_id": job_id}

        # Update PipeExecution with current info
        syncer.update_pipe_execution(job_info)

        if syncer.is_job_terminal(job_info):
            # Job finished - log and stop
            logger.info(
                f"Job {job_id} reached terminal state: {job_info['state']} "
                f"(elapsed: {job_info.get('elapsed', 'unknown')})",
            )
            return {
                "status": "completed",
                "job_id": job_id,
                "state": job_info["state"],
                "elapsed": job_info.get("elapsed"),
            }

        # Job still running - reschedule for 60 seconds from now
        logger.debug(f"Job {job_id} still {job_info['state']}, rescheduling...")
        _run_later(
            "processes.tasks.run_job_status_syncer",
            (job_id, cluster_id),
            name=f"job_status_{job_id}",
            delay=SACCT_POLL_INTERVAL,
        )
        return {"status": "running", "job_id": job_id, "state": job_info["state"]}

    except Exception as e:
        logger.error(f"Error in job status syncer for {job_id}: {e}")
        # Reschedule anyway to retry (with backoff)
        _run_later(
            "processes.tasks.run_job_status_syncer",
            (job_id, cluster_id),
            name=f"job_status_{job_id}",
            delay=SACCT_ERROR_BACKOFF,
        )
        return {"status": "error", "job_id": job_id, "error": str(e)}


def start_job_status_syncer(job_id: str, cluster_id: str = "czii"):
    """
    Start the job status syncer for a newly submitted job.

    This starts a self-rescheduling task that polls sacct every 60 seconds
    until the job reaches a terminal state (completed, failed, cancelled, etc.).

    Args:
        job_id: SLURM job ID to track
        cluster_id: Cluster to query (czii or bruno)

    Returns:
        str: Django-Q task ID
    """
    task_id = async_task(
        "processes.tasks.run_job_status_syncer",
        job_id,
        cluster_id,
        task_name=f"job_status_{job_id}",
    )

    logger.info(f"Started job status syncer for job {job_id} on {cluster_id}. Task ID: {task_id}")

    return task_id
