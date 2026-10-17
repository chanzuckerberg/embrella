"""Read a deposition job's SLURM log tail over SSH, as the service account."""

import logging

from django.core.cache import cache
from workflow.processors import get_processor

from common import clusterio

logger = logging.getLogger(__name__)

MAX_LOG_BYTES = 64 * 1024
# Throttle live SSH reads so polling can't open a connection per request (like the workflow log reader).
LIVE_LOG_COOLDOWN_SECONDS = 15

_PUSH_STATES = {"push_submitted", "push_running", "completed"}
_PROCESSOR = {"prep": "deposition-prep", "push": "deposition-push"}


def _active_attempt(job):
    """(phase, slurm_job_id) for the attempt whose log to show."""
    if job.state in _PUSH_STATES or (job.state == "failed" and job.push_slurm_job_id):
        return "push", job.push_slurm_job_id
    return "prep", job.prep_slurm_job_id


def read_slurm_tail(cluster_id, auth, phase, slurm_job_id):
    """Last MAX_LOG_BYTES of the job's default slurm-<id>.out."""
    script_dir = get_processor(_PROCESSOR[phase]).get_script_directory(cluster=cluster_id)
    path = f"{script_dir.rstrip('/')}/slurm-{slurm_job_id}.out"
    return clusterio.read_remote_file_tail(cluster_id, path, max_bytes=MAX_LOG_BYTES, auth=auth)


def capture_failure_tail(cluster_id, auth, phase, slurm_job_id):
    """Best-effort SLURM .out tail to snapshot onto a failed job, so the UI can show why
    even once live reads stop. Returns None if the read can't be made."""
    if not (cluster_id and slurm_job_id and auth):
        return None
    try:
        return read_slurm_tail(cluster_id, auth, phase, slurm_job_id)
    except Exception:
        logger.warning("Couldn't capture SLURM log tail for %s job %s", phase, slurm_job_id, exc_info=True)
        return None


def fetch_job_logs(dataset, *, is_owner, phase=None):
    """Owner-only SLURM tail, live or saved; omit phase to read the current attempt."""
    job = getattr(dataset, "job", None)
    if job is None:
        return {"logs": "", "state": None, "source": "none"}

    current_phase, _ = _active_attempt(job)
    phase = phase or current_phase
    slurm_job_id = getattr(job, f"{phase}_slurm_job_id")
    excerpt = job.log_excerpt if is_owner and phase == current_phase else ""
    stored = {"logs": excerpt or "", "state": job.state, "phase": phase, "source": "stored"}
    cluster_id = job.cluster_id
    if not is_owner or not slurm_job_id or not cluster_id:
        return stored

    # Cache reads and failures per cluster + job for 15 seconds (reads are as one service account).
    cache_key = f"deposition-log:{cluster_id}:{job.pk}:{phase}:{slurm_job_id}"
    cached = cache.get(cache_key)
    if cached is not None and cached["state"] == job.state:
        return cached
    # State changed: re-read, since a cached running tail can hide the final output or failure excerpt.

    try:
        auth = clusterio.get_auth_service_user()
    except Exception:
        # No service credentials (SSH disabled / missing key) - fall back, don't 500.
        logger.warning("No service credentials to read the SLURM log for dataset %s", dataset.pk, exc_info=True)
        return stored

    try:
        text = read_slurm_tail(cluster_id, auth, phase, slurm_job_id)
    except Exception:
        # "unavailable" (not "stored") tells the client the live read failed vs. there being no log.
        logger.warning("Couldn't read SLURM log for dataset %s job %s", dataset.pk, slurm_job_id, exc_info=True)
        unavailable = {**stored, "source": "unavailable"}
        cache.set(cache_key, unavailable, LIVE_LOG_COOLDOWN_SECONDS)
        return unavailable

    result = {"logs": text, "state": job.state, "phase": phase, "job_id": slurm_job_id, "source": "live"}
    cache.set(cache_key, result, LIVE_LOG_COOLDOWN_SECONDS)
    return result
