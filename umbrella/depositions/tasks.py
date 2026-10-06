"""Django-Q tasks for deposition submit jobs."""

import logging
from datetime import timedelta

from django_q.tasks import async_task

from depositions.models import DatasetJob
from depositions.services import submission

logger = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=60)
NOT_LISTED_DELAY = timedelta(seconds=30)
ERROR_BACKOFF = timedelta(seconds=120)
MAX_WAIT_ATTEMPTS = 20

_COMPLETION = {"prep": submission.on_prep_complete, "push": submission.on_push_complete}
_ATTEMPT_FIELD = {"prep": "prep_slurm_job_id", "push": "push_slurm_job_id"}


def _exit_ok(exit_code):
    return not exit_code or exit_code.split(":")[0] == "0"


def _give_up(job, phase, cluster_id, slurm_job_id, reason):
    from depositions.services.launch import cancel_deposition_job

    logger.warning("Deposition %s syncer giving up on DatasetJob %s: %s", phase, job.pk, reason)
    if slurm_job_id:
        try:
            cancel_deposition_job(cluster_id=cluster_id, job_id=slurm_job_id)
        except Exception:
            logger.exception(
                "Could not cancel %s job %s on give-up; leaving DatasetJob %s for an operator.",
                phase,
                slurm_job_id,
                job.pk,
            )
            return False
    _COMPLETION[phase](job, False, job_id=slurm_job_id or None, error_message=reason)
    return True


def start_deposition_job_syncer(dataset_job_id, phase, cluster_id, expected_job_id):
    """Start the poller for a submitted prep/push job attempt."""
    return async_task(
        "depositions.tasks.run_deposition_job_syncer",
        dataset_job_id,
        phase,
        cluster_id,
        expected_job_id,
        task_name=f"deposition_{phase}_{dataset_job_id}",
    )


def _reschedule(dataset_job_id, phase, cluster_id, expected_job_id, attempts, delay):
    from processes.tasks.syncer_tasks import _run_later

    _run_later(
        "depositions.tasks.run_deposition_job_syncer",
        (dataset_job_id, phase, cluster_id, expected_job_id, attempts),
        name=f"deposition_{phase}_{dataset_job_id}",
        delay=delay,
    )


def run_deposition_job_syncer(dataset_job_id, phase, cluster_id, expected_job_id, attempts=0):
    from workflow.syncers import JobStatusSyncer

    try:
        job = DatasetJob.objects.get(pk=dataset_job_id)
    except DatasetJob.DoesNotExist:
        logger.warning("Deposition syncer: DatasetJob %s is gone; stopping.", dataset_job_id)
        return {"status": "gone"}

    slurm_job_id = getattr(job, _ATTEMPT_FIELD[phase])
    if slurm_job_id and slurm_job_id != expected_job_id:
        # A retry replaced the attempt we were started for; let its own poller take over.
        logger.info("Deposition syncer: %s attempt changed (%s != %s); stopping.", phase, slurm_job_id, expected_job_id)
        return {"status": "superseded"}
    if not slurm_job_id:
        if attempts >= MAX_WAIT_ATTEMPTS:
            logger.warning(
                "Deposition %s poller for DatasetJob %s stopping: no SLURM id on the row.", phase, dataset_job_id
            )
            return {"status": "gave_up", "reason": "no_id"}
        _reschedule(dataset_job_id, phase, cluster_id, expected_job_id, attempts + 1, NOT_LISTED_DELAY)
        return {"status": "waiting_id"}

    syncer = JobStatusSyncer(job_id=slurm_job_id, cluster_id=cluster_id)
    try:
        info = syncer.get_job_info_from_sacct()
        if info is None:
            if attempts >= MAX_WAIT_ATTEMPTS:
                _give_up(job, phase, cluster_id, slurm_job_id, f"Deposition {phase} job {slurm_job_id} never in sacct.")
                return {"status": "gave_up", "reason": "not_in_sacct"}
            _reschedule(dataset_job_id, phase, cluster_id, expected_job_id, attempts + 1, NOT_LISTED_DELAY)
            return {"status": "waiting"}
        if not syncer.is_job_terminal(info):
            if info["state"] == "RUNNING":
                submission.on_job_running(job, phase, job_id=slurm_job_id)
            # Job is live: reset the no-progress counter and keep polling.
            _reschedule(dataset_job_id, phase, cluster_id, expected_job_id, 0, POLL_INTERVAL)
            return {"status": "running", "state": info["state"]}
        success = info["state"] == "COMPLETED" and _exit_ok(info.get("exit_code"))
        _COMPLETION[phase](
            job,
            success,
            job_id=slurm_job_id,
            error_message=None
            if success
            else f"Deposition {phase} job ended {info['state']} (exit {info.get('exit_code')}).",
        )
        return {"status": "terminal", "state": info["state"], "success": success}
    except Exception as e:
        logger.error("Deposition syncer error (%s job %s): %s", phase, slurm_job_id, e)
        if attempts >= MAX_WAIT_ATTEMPTS:
            _give_up(job, phase, cluster_id, slurm_job_id, f"Deposition {phase} syncer kept erroring: {e}")
            return {"status": "gave_up", "reason": "error"}
        _reschedule(dataset_job_id, phase, cluster_id, expected_job_id, attempts + 1, ERROR_BACKOFF)
        return {"status": "error", "error": str(e)}
