"""Read a deposition job's SLURM log tail over SSH, as the submission owner."""

import logging

from accounts.cluster_usernames import MissingClusterCredentialsError
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


def _read_slurm_tail(cluster_id, auth, phase, slurm_job_id):
    """Last MAX_LOG_BYTES of the job's default slurm-<id>.out."""
    script_dir = get_processor(_PROCESSOR[phase]).get_script_directory(cluster=cluster_id)
    path = f"{script_dir.rstrip('/')}/slurm-{slurm_job_id}.out"
    ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id, auth=auth)
    try:
        sftp = ssh.open_sftp()
        try:
            size = sftp.stat(path).st_size
            with sftp.file(path, "r") as handle:
                if size > MAX_LOG_BYTES:
                    handle.seek(size - MAX_LOG_BYTES)
                # Cap the read: the file can grow past `size` between stat() and read().
                data = handle.read(MAX_LOG_BYTES)
            return data.decode("utf-8", "replace")
        finally:
            sftp.close()
    finally:
        ssh.close()


def fetch_job_logs(dataset, *, user):
    """Live SLURM .out tail for the dataset's current job"""
    job = getattr(dataset, "job", None)
    if job is None:
        return {"logs": "", "state": None, "source": "none"}

    phase, slurm_job_id = _active_attempt(job)
    stored = {"logs": job.log_excerpt or "", "state": job.state, "phase": phase, "source": "stored"}
    cluster_id = job.cluster_id
    if not slurm_job_id or not cluster_id:
        return stored

    # Within the cooldown, serve the cached read instead of reopening SSH.
    cache_key = f"deposition-log:{job.pk}:{slurm_job_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        auth, error = clusterio.get_auth_for_user(user, cluster_id)
    except MissingClusterCredentialsError:
        return stored
    if error or not auth:
        return stored

    try:
        text = _read_slurm_tail(cluster_id, auth, phase, slurm_job_id)
    except Exception:
        logger.warning("Couldn't read SLURM log for dataset %s job %s", dataset.pk, slurm_job_id, exc_info=True)
        return stored

    result = {"logs": text, "state": job.state, "phase": phase, "job_id": slurm_job_id, "source": "live"}
    cache.set(cache_key, result, LIVE_LOG_COOLDOWN_SECONDS)
    return result
