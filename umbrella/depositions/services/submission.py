"""DatasetJob state transitions for the submit flow."""

import logging

from django.db import transaction
from django.utils import timezone

from depositions.models import DatasetJob
from depositions.services.exceptions import SubmissionValidationError

logger = logging.getLogger(__name__)

PREP_ACTIVE = ("prep_submitted", "prep_running")
PUSH_ACTIVE = ("push_submitted", "push_running")

# phase -> (submitted_state, running_state, attempt_field)
_RUNNING = {
    "prep": ("prep_submitted", "prep_running", "prep_slurm_job_id"),
    "push": ("push_submitted", "push_running", "push_slurm_job_id"),
}


def apply_status(job):
    # Mirror the job state onto the API-facing Dataset.status.
    job.dataset.status = job.dataset_status
    job.dataset.save(update_fields=["status", "updated_at"])


def on_job_running(job, phase, *, job_id):
    """Flip {phase}_submitted -> {phase}_running on the first RUNNING sacct poll. Idempotent."""
    submitted, running, attempt_field = _RUNNING[phase]
    updated = DatasetJob.objects.filter(pk=job.pk, state=submitted, **{attempt_field: job_id}).update(
        state=running, updated_at=timezone.now()
    )
    if updated:
        job.refresh_from_db()
        apply_status(job)
    return job


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
    apply_status(job)
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


def start_push(job, *, launch, cancel=None):
    """Claim prep_completed -> push_submitted, launch the job, and store its id."""
    with transaction.atomic():
        claimed = DatasetJob.objects.filter(pk=job.pk, state="prep_completed").update(
            state="push_submitted", error_message="", completed_at=None, push_slurm_job_id=""
        )
        job.refresh_from_db()
        if claimed:
            apply_status(job)
    if not claimed:
        raise SubmissionValidationError(f"Push can only start from prep_completed, not {job.state!r}.")
    job_id = None
    try:
        from depositions.services.launch import LaunchError

        job_id = launch(job)
        if not job_id:
            raise LaunchError("Push launch returned an empty SLURM job id.")
        logger.info("Push launched for DatasetJob %s (SLURM job %s)", job.pk, job_id)
        recorded = DatasetJob.objects.filter(pk=job.pk, state="push_submitted", push_slurm_job_id="").update(
            push_slurm_job_id=job_id, updated_at=timezone.now()
        )
        if not recorded:
            job.refresh_from_db()
            if job.state == "push_submitted":
                raise LaunchError("Lost the push claim before the SLURM id could be recorded.")
    except Exception:
        if job_id and cancel is not None:
            try:
                cancel(job_id)
            except Exception:
                # Unconfirmed cancel: leave for an operator, not retryable into a double-upload.
                logger.exception("Couldn't cancel orphaned push job %s for DatasetJob %s", job_id, job.pk)
                raise
        elif job_id:
            raise
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
