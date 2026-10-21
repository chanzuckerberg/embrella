"""DatasetJob state transitions for the submit flow."""

import logging

from django.db import transaction
from django.utils import timezone

from depositions.models import DatasetJob
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.validation import require_validation

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


def on_prep_complete(
    job, success, *, job_id=None, error_message=None, log_excerpt=None, sync_summary=None, validation=None
):
    """Complete the active prep attempt; validation gates upload separately."""
    if success:
        # Drop any failure left from an earlier attempt.
        fields = {
            "state": "prep_completed",
            "prep_completed_at": timezone.now(),
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
    if sync_summary is not None:
        fields["sync_summary"] = sync_summary
    fields["validation"] = validation if success else None
    return _record_completion(
        job, active_states=PREP_ACTIVE, attempt_field="prep_slurm_job_id", job_id=job_id, fields=fields
    )


def reset_preparation(dataset):
    """Reset a prepared or failed dataset to an editable draft, clearing its attempt."""
    db = dataset._state.db
    try:
        job = DatasetJob.objects.using(db).get(dataset=dataset)
    except DatasetJob.DoesNotExist:
        raise SubmissionValidationError("This dataset hasn't been prepared yet.")
    with transaction.atomic(using=db):
        claimed = (
            DatasetJob.objects.using(db)
            .filter(pk=job.pk, state__in=("prep_completed", "failed"))
            .update(
                state="pending",
                validation=None,
                error_message="",
                log_excerpt="",
                prep_slurm_job_id="",
                push_slurm_job_id="",
                sync_progress=None,
                sync_summary=None,
                push_progress=None,
                started_at=None,
                prep_completed_at=None,
                completed_at=None,
            )
        )
        if not claimed:
            job.refresh_from_db()
            raise SubmissionValidationError(f"Preparation can't be reset while the dataset is {job.state!r}.")
        job.refresh_from_db()
        apply_status(job)
    return job


def start_push(job, *, launch, cancel=None):
    """Claim prep_completed -> push_submitted, launch the job, and store its id."""
    with transaction.atomic():
        claimed = (
            DatasetJob.objects.filter(
                pk=job.pk,
                state="prep_completed",
                # Claim the same prep attempt used to build the upload paths.
                prep_slurm_job_id=job.prep_slurm_job_id,
                cluster_id=job.cluster_id,
                validation__status="passed",
                # literal, not F("prep_slurm_job_id"): JSON-key-to-column compare is fragile on MySQL.
                validation__attempt=job.prep_slurm_job_id,
                validation__blocking_issues=[],
            )
            .exclude(prep_slurm_job_id="")
            .update(
                state="push_submitted", error_message="", completed_at=None, push_slurm_job_id="", push_progress=None
            )
        )
        job.refresh_from_db()
        if claimed:
            apply_status(job)
    if not claimed:
        require_validation(job)
        raise SubmissionValidationError("Preparation changed before upload could start; refresh and try again.")
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
