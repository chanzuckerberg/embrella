"""DatasetJob state transitions for the submit flow."""

import logging

from django.db import transaction
from django.utils import timezone

from depositions.models import DatasetJob

logger = logging.getLogger(__name__)

PREP_ACTIVE = ("prep_submitted", "prep_running")
PUSH_ACTIVE = ("push_submitted", "push_running")


def _apply_status(job):
    # Mirror the job state onto the API-facing Dataset.status.
    job.dataset.status = job.dataset_status
    job.dataset.save(update_fields=["status", "updated_at"])


@transaction.atomic
def _record_completion(job, *, active_states, attempt_field, job_id, fields, require_attempt=False):
    # Update only jobs still in the expected state; ignore stale callbacks.
    qs = DatasetJob.objects.filter(pk=job.pk, state__in=active_states)
    if require_attempt:
        qs = qs.exclude(**{attempt_field: ""}).exclude(**{f"{attempt_field}__isnull": True})
    if job_id is not None:
        qs = qs.filter(**{attempt_field: job_id})
    if not qs.update(**fields):
        job.refresh_from_db()
        logger.warning(
            "Completion for DatasetJob %s did not match an active attempt (now %r, %s=%r)",
            job.pk,
            job.state,
            attempt_field,
            getattr(job, attempt_field),
        )
        return job
    job.refresh_from_db()
    _apply_status(job)
    return job


def on_prep_complete(job, success, *, job_id=None, error_message=None, log_excerpt=None):
    """Mark a finished prep job prep_completed, or failed. Ignored unless the row is still an active prep attempt."""
    if success:
        # Drop any failure left from an earlier attempt.
        fields = {
            "state": "prep_completed",
            "error_message": "",
            "completed_at": None,
            "log_excerpt": log_excerpt or "",
        }
    else:
        fields = {
            "state": "failed",
            "error_message": error_message or "Deposition prep failed.",
            "completed_at": timezone.now(),
        }
        if log_excerpt is not None:
            fields["log_excerpt"] = log_excerpt
    return _record_completion(
        job, active_states=PREP_ACTIVE, attempt_field="prep_slurm_job_id", job_id=job_id, fields=fields
    )


def start_push(job, *, launch):
    """User-triggered push: claim prep_completed -> push_submitted, then launch the job."""
    # Compare-and-set so two Submit clicks can't both launch; claim before the slow launch.
    with transaction.atomic():
        claimed = DatasetJob.objects.filter(pk=job.pk, state="prep_completed").update(
            state="push_submitted", error_message="", completed_at=None, push_slurm_job_id=""
        )
        job.refresh_from_db()
        if claimed:
            _apply_status(job)
    if not claimed:
        raise ValueError(f"Push can only start from prep_completed, not {job.state!r}.")
    try:
        job_id = launch(job)
        if not job_id:
            raise ValueError("Push launch returned an empty SLURM job id.")
    except Exception:
        # Fail only the row we just claimed: still push_submitted with the blank id. Do NOT pass
        # require_attempt here — it would exclude that blank id and the failed row would never match.
        _record_completion(
            job,
            active_states=("push_submitted",),
            attempt_field="push_slurm_job_id",
            job_id="",
            fields={
                "state": "failed",
                "error_message": "Failed to submit the push job.",
                "completed_at": timezone.now(),
                "updated_at": timezone.now(),
            },
        )
        raise
    # Log the id before the write: if that write fails, an operator can restore push_slurm_job_id
    # from this line. (A crash inside launch, before it returns, leaves no id and no log.)
    logger.info("Push launched for DatasetJob %s (SLURM job %s)", job.pk, job_id)
    DatasetJob.objects.filter(pk=job.pk, state="push_submitted", push_slurm_job_id="").update(
        push_slurm_job_id=job_id, updated_at=timezone.now()
    )
    job.refresh_from_db()
    return job


def on_push_complete(job, success, *, job_id=None, error_message=None, log_excerpt=None):
    """Mark a finished push job completed, or failed. Ignored unless the row is still an active push attempt with a stored SLURM id."""
    if success:
        fields = {
            "state": "completed",
            "error_message": "",
            "completed_at": timezone.now(),
            "log_excerpt": log_excerpt or "",
        }
    else:
        fields = {
            "state": "failed",
            "error_message": error_message or "Deposition push failed.",
            "completed_at": timezone.now(),
        }
        if log_excerpt is not None:
            fields["log_excerpt"] = log_excerpt
    return _record_completion(
        job,
        active_states=PUSH_ACTIVE,
        attempt_field="push_slurm_job_id",
        job_id=job_id,
        fields=fields,
        require_attempt=True,
    )
