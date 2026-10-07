"""Submit a dataset: stage the deposition config on the cluster and launch its prep job.."""

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from processes.services.cluster_resolver import cluster_id_for_run, get_default_cluster_id
from stores.paths import resolve_dir

from common import clusterio
from depositions import tasks
from depositions.models import DatasetJob, Deposition, DepositionAnnotation
from depositions.services.dataprep_config import dataprep_config_yaml, dataset_is_ready, resolve_sync_destination
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.launch import LaunchError, cancel_deposition_job, launch_deposition_job
from depositions.services.submission import PREP_ACTIVE, apply_status, on_push_complete, start_push

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "dataprep_config.yaml"


def _cluster_for_dataset(dataset):
    session = dataset.sessions.select_related("msi_session").order_by("msi_session__name").first()
    if session is None:
        return get_default_cluster_id()
    run = session.aretomo_run_name or ""
    run_number = run if run.startswith("run") else f"run{run}"
    return cluster_id_for_run(session.msi_session.name, run_number)


def _user_auth(user, cluster_id):
    auth, error = clusterio.get_auth_for_user(user, cluster_id)
    if error or not auth:
        raise SubmissionValidationError("The configured cluster is unavailable for submission.")
    return auth


def submit_dataset_prep(dataset, *, user):
    """Write the deposition config and launch this dataset's prep job. Returns the DatasetJob."""
    deposition = dataset.deposition
    if deposition.deposition_id is None or dataset.dataset_id is None:
        raise SubmissionValidationError("Reserve deposition_id and dataset_id before submitting.")
    if not dataset_is_ready(dataset):
        raise SubmissionValidationError("This dataset isn't ready to submit — add sessions and run auto-fill first.")
    if DepositionAnnotation.objects.filter(session__dataset=dataset, is_selected=True).exists():
        # Annotation export isn't wired yet; refuse rather than mark the dataset done without it.
        # TODO(#1291): annotation export.
        raise SubmissionValidationError(
            "Depositing annotations isn't supported yet; deselect them to submit this dataset."
        )

    cluster_id = _cluster_for_dataset(dataset)
    auth = _user_auth(user, cluster_id)
    db = dataset._state.db
    # Claim one queued/running prep per deposition before freezing the shared config.
    # Otherwise an older queued job could overwrite a newer sibling's config.
    with transaction.atomic(using=db):
        Deposition.objects.using(db).select_for_update().get(pk=deposition.pk)
        if (
            DatasetJob.objects.using(db)
            .filter(dataset__deposition=deposition, state__in=PREP_ACTIVE)
            .exclude(dataset_id=dataset.pk)
            .exists()
        ):
            raise SubmissionValidationError(
                "Another dataset in this deposition is queued or running prep; wait for it to finish before submitting."
            )
        job, _ = DatasetJob.objects.using(db).get_or_create(dataset=dataset)
        claimed = (
            DatasetJob.objects.using(db)
            .filter(pk=job.pk, state__in=("pending", "failed"))
            .update(state="prep_submitted", prep_slurm_job_id="", error_message="", started_at=timezone.now())
        )
        if not claimed:
            job.refresh_from_db()
            raise SubmissionValidationError(f"Dataset is already {job.state}; it can't be submitted again.")
        job.refresh_from_db()
        apply_status(job)

    slurm_job_id = None
    try:
        # Resolve paths inside the try so a resolution failure rolls the claim back, not strands it.
        output_dir = resolve_dir("deposition_staging", cluster=cluster_id, deposition_id=deposition.deposition_id)
        config_path = f"{output_dir.rstrip('/')}/{CONFIG_FILENAME}"
        required_siblings = set(
            DatasetJob.objects.using(db)
            .filter(dataset__deposition=deposition)
            .filter(Q(staged_at__isnull=False) | Q(state__in=DatasetJob.LOCKED_STATES))
            .values_list("dataset__dataset_id", flat=True)
        )
        required_ids = required_siblings | {dataset.dataset_id}
        config_yaml = dataprep_config_yaml(
            deposition,
            output_dir=output_dir,
            sync_destination=resolve_sync_destination(cluster=cluster_id),
            required_dataset_ids=required_ids,
        )
        params = {
            "output_dir": output_dir,
            "config_path": config_path,
            "config_yaml": config_yaml,
            "session_names": list(dataset.sessions.values_list("msi_session__name", flat=True)),
            "run_validate": False,
        }
        job_name = f"deposition_prep_{deposition.deposition_id}_{dataset.dataset_id}"
        slurm_job_id = launch_deposition_job(
            processor_name="deposition-prep", params=params, cluster_id=cluster_id, job_name=job_name, auth=auth
        )
        if not slurm_job_id:
            raise LaunchError("Prep launch returned an empty SLURM job id.")
        recorded = (
            DatasetJob.objects.using(db)
            .filter(pk=job.pk, state="prep_submitted", prep_slurm_job_id="")
            .update(prep_slurm_job_id=slurm_job_id, staged_at=timezone.now(), cluster_id=cluster_id)
        )
        if not recorded:
            raise LaunchError("Lost the prep claim before the SLURM id could be recorded.")
        tasks.start_deposition_job_syncer(job.id, "prep", cluster_id, slurm_job_id)
    except Exception:
        # Cancel the orphaned job, then fail the row so the user can retry.
        if slurm_job_id and cluster_id:
            try:
                cancel_deposition_job(cluster_id=cluster_id, job_id=slurm_job_id, auth=auth)
            except Exception:
                # Can't confirm it stopped — leave it at prep_submitted for an operator, not retryable.
                logger.exception(
                    "Couldn't cancel orphaned prep job %s on %s; leaving row for operator.", slurm_job_id, cluster_id
                )
                raise
        DatasetJob.objects.using(db).filter(pk=job.pk, state="prep_submitted").update(
            state="failed", error_message="Failed to submit the prep job.", completed_at=timezone.now()
        )
        job.refresh_from_db()
        apply_status(job)
        raise

    job.refresh_from_db()
    return job


def submit_dataset_push(dataset, *, user):
    """Launch this dataset's push (S3 upload) job from a prep_completed state. Returns the DatasetJob."""
    deposition = dataset.deposition
    if deposition.deposition_id is None or dataset.dataset_id is None:
        raise SubmissionValidationError("Reserve deposition_id and dataset_id before pushing.")
    try:
        job = dataset.job
    except DatasetJob.DoesNotExist:
        raise SubmissionValidationError("This dataset hasn't been prepared yet; submit it first.")

    # Use the cluster prep staged on, not one re-derived from (mutable) metadata.
    cluster_id = job.cluster_id or _cluster_for_dataset(dataset)
    auth = _user_auth(user, cluster_id)
    output_dir = resolve_dir("deposition_staging", cluster=cluster_id, deposition_id=deposition.deposition_id)
    base = output_dir.rstrip("/")
    staged_dir = f"{base}/{dataset.dataset_id}"
    s3_dest = f"{resolve_sync_destination(cluster=cluster_id)}/{deposition.deposition_id}/{dataset.dataset_id}"

    def launch(_job):
        job_name = f"deposition_push_{deposition.deposition_id}_{dataset.dataset_id}"
        return launch_deposition_job(
            processor_name="deposition-push",
            params={"staged_dir": staged_dir, "s3_dest": s3_dest},
            cluster_id=cluster_id,
            job_name=job_name,
            auth=auth,
        )

    def cancel(job_id):
        cancel_deposition_job(cluster_id=cluster_id, job_id=job_id, auth=auth)

    job = start_push(job, launch=launch, cancel=cancel)
    try:
        tasks.start_deposition_job_syncer(job.id, "push", cluster_id, job.push_slurm_job_id)
    except Exception:
        if job.push_slurm_job_id:
            try:
                cancel_deposition_job(cluster_id=cluster_id, job_id=job.push_slurm_job_id, auth=auth)
            except Exception:
                logger.exception(
                    "Couldn't cancel orphaned push job %s on %s; leaving row for operator.",
                    job.push_slurm_job_id,
                    cluster_id,
                )
                raise
        on_push_complete(job, False, job_id=job.push_slurm_job_id, error_message="Failed to start the push monitor.")
        raise
    return job
