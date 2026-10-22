"""Tests for the dataset submit orchestration."""

import pytest
import yaml
from cryo_grids.models import Sample
from django.contrib.auth.models import User
from django.utils import timezone
from stores.models import Cluster, DataKind, PathType
from stores.paths import resolve_dir

from depositions.models import (
    Dataset,
    DatasetJob,
    Deposition,
    DepositionAnnotation,
    DepositionSession,
    TiltseriesMetadata,
)
from depositions.services import submit
from depositions.services.dataprep_config import dataprep_config_yaml
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.submission import on_prep_complete


def _raise_no_creds():
    raise RuntimeError("service credentials unavailable")


@pytest.fixture
def dataset(db, test_msi_session):
    deposition = Deposition.objects.create(
        title="Dep",
        deposition_id=1,
        authors_json=[{"full_name": "Ada Lovelace", "is_primary": True, "is_corresponding": True}],
    )
    sample = Sample.objects.create(name="submission-test-sample", sample_type="in_vitro")
    ds = Dataset.objects.create(
        deposition=deposition, title="DS", description="Reviewed description", dataset_id=2, sample=sample
    )
    session = DepositionSession.objects.create(dataset=ds, msi_session=test_msi_session, aretomo_run_name="run001")
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/a"}, "acquisition": {}}
    )
    return ds


@pytest.fixture
def mocks(monkeypatch, db):
    Cluster.objects.get_or_create(cluster_id="cluster-a")
    PathType.objects.filter(data_kind__data_type="deposition_staging", cluster=None).update(
        overlay_path="/test/depositions/{deposition_id}/"
    )
    PathType.objects.filter(data_kind__data_type="deposition_sync_destination", cluster=None).update(
        overlay_path="s3://example-bucket/depositions"
    )
    calls = {"written": None, "launched": None, "synced": None, "required_ids": None}

    def write(cluster_id, path, content):
        calls["written"] = (cluster_id, path, content)

    def launch(*, processor_name, params, cluster_id, job_name, auth):
        calls["launched"] = {
            "processor": processor_name,
            "params": params,
            "cluster": cluster_id,
            "job_name": job_name,
            "auth": auth,
        }
        return "slurm-500"

    calls["auth"] = {"username": "service-user", "pkey": "test-key"}
    monkeypatch.setattr(submit.clusterio, "get_auth_service_user", lambda: calls["auth"])
    monkeypatch.setattr(submit, "cluster_id_for_run", lambda *a, **k: "cluster-a")
    monkeypatch.setattr(submit.clusterio, "ensure_remote_dir", lambda *a: calls.__setitem__("mkdir", a))
    monkeypatch.setattr(submit.clusterio, "write_remote_file_atomic", write)

    def config_yaml(deposition, *, output_dir, sync_destination=None, required_dataset_ids=None):
        calls["sync_destination"] = sync_destination
        calls["required_ids"] = required_dataset_ids
        return "yaml-text"

    monkeypatch.setattr(submit, "dataprep_config_yaml", config_yaml)
    monkeypatch.setattr(submit, "launch_deposition_job", launch)
    monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", lambda *a: calls.__setitem__("synced", a))
    return calls


@pytest.mark.django_db
class TestSubmitDatasetPrep:
    def test_incomplete_metadata_does_not_claim_or_launch_preparation(self, dataset, mocks):
        dataset.description = " "
        dataset.sample.sample_type = "cell_line"
        dataset.sample.save(update_fields=["sample_type"])
        dataset.save(update_fields=["description"])
        with pytest.raises(SubmissionValidationError) as error:
            submit.submit_dataset_prep(dataset)
        assert "Dataset description is required" in str(error.value)
        assert "Organism name" in str(error.value)
        assert "Cell strain" in str(error.value)
        assert mocks["launched"] is None
        assert not DatasetJob.objects.filter(dataset=dataset).exists()
        dataset.refresh_from_db()
        assert dataset.status == "draft"

    def test_missing_author_stops_before_cluster_launch(self, dataset, mocks):
        dataset.deposition.authors_json = [{"author_id": 987654321}]
        dataset.deposition.save(update_fields=["authors_json"])
        with pytest.raises(SubmissionValidationError, match="Review the authors"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None
        assert not DatasetJob.objects.filter(dataset=dataset).exists()

    def test_happy_path(self, dataset, mocks, test_msi_session):
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert job.prep_slurm_job_id == "slurm-500"
        dataset.refresh_from_db()
        assert dataset.status == "syncing"
        assert mocks["written"] is None
        assert "mkdir" not in mocks
        # Prep scoped to this dataset's sessions.
        launched = mocks["launched"]
        assert launched["params"]["session_names"] == [test_msi_session.name]
        assert launched["job_name"] == "deposition_prep_1_2"
        assert launched["params"]["config_yaml"] == "yaml-text"
        staging_dir = resolve_dir("deposition_staging", cluster="cluster-a", deposition_id=1).rstrip("/")
        assert launched["params"]["config_path"] == f"{staging_dir}/dataprep_config.yaml"
        assert launched["auth"] is mocks["auth"]
        assert mocks["synced"] == (job.id, "prep", "cluster-a", "slurm-500")

    def test_rejects_unreserved_ids(self, dataset, mocks):
        dataset.dataset_id = None  # checked on the passed object
        with pytest.raises(SubmissionValidationError, match="Reserve"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_rejects_resubmit_while_in_flight(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_running", prep_slurm_job_id="old")
        with pytest.raises(SubmissionValidationError, match="already"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_selected_annotations_no_longer_block_submission(self, dataset, mocks):
        session = dataset.sessions.get()
        DepositionAnnotation.objects.create(session=session, copick_kind="picks", copick_ref="ribosome:alice/0")
        assert submit.submit_dataset_prep(dataset).state == "prep_submitted"
        assert mocks["launched"] is not None

    def test_deselected_annotations_do_not_block(self, dataset, mocks):
        session = dataset.sessions.get()
        DepositionAnnotation.objects.create(
            session=session, copick_kind="picks", copick_ref="ribosome-0", is_selected=False
        )
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert mocks["launched"] is not None

    def test_rejects_not_ready_dataset(self, dataset, mocks):
        TiltseriesMetadata.objects.filter(session__dataset=dataset).delete()
        with pytest.raises(SubmissionValidationError, match="ready to submit"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_retry_after_failure(self, dataset, mocks):
        DatasetJob.objects.create(
            dataset=dataset,
            state="failed",
            error_message="boom",
            validation={"status": "passed", "attempt": "old"},
            sync_progress={"done": 5},
            sync_summary={"objects": 5},
            push_progress={"done": 100},
        )
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert not job.error_message
        assert job.validation is None
        assert job.sync_progress is None and job.sync_summary is None and job.push_progress is None

    def test_restart_clears_prior_push_attempt(self, dataset, mocks):
        # A prep restart after a failed push must drop the stale push id so the log reader
        # doesn't surface the old upload log if this prep also fails.
        DatasetJob.objects.create(
            dataset=dataset,
            state="failed",
            push_slurm_job_id="999",
            error_message="push boom",
            log_excerpt="old upload log",
            prep_completed_at="2026-10-14T12:00:00Z",
            completed_at="2026-10-14T12:01:00Z",
        )
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert job.push_slurm_job_id == ""
        assert job.log_excerpt == ""  # old attempt's output cleared too
        assert job.prep_completed_at is None
        assert job.completed_at is None

    def test_path_resolution_failure_fails_row_without_launching(self, dataset, mocks, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("no deposition_staging PathType")

        monkeypatch.setattr(submit, "resolve_dir", boom)
        with pytest.raises(RuntimeError):
            submit.submit_dataset_prep(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"  # rolled back, not stranded at prep_submitted
        assert mocks["launched"] is None

    def test_poller_start_failure_cancels_job_and_fails_row(self, dataset, mocks, monkeypatch):
        cancelled = {}

        def boom(*a):
            raise RuntimeError("django-q is down")

        monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", boom)
        monkeypatch.setattr(
            submit,
            "cancel_deposition_job",
            lambda *, cluster_id, job_id, auth: cancelled.update(id=job_id, cluster=cluster_id, auth=auth),
        )
        with pytest.raises(RuntimeError):
            submit.submit_dataset_prep(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        # The job reached the cluster, so it must be cancelled rather than left running unwatched.
        assert cancelled == {"id": "slurm-500", "cluster": "cluster-a", "auth": mocks["auth"]}

    def test_poller_start_failure_leaves_row_if_cancel_fails(self, dataset, mocks, monkeypatch):
        def boom(*a):
            raise RuntimeError("django-q is down")

        def bad_cancel(*, cluster_id, job_id, auth):
            raise OSError("scancel failed")

        monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", boom)
        monkeypatch.setattr(submit, "cancel_deposition_job", bad_cancel)
        with pytest.raises(OSError, match="scancel failed"):
            submit.submit_dataset_prep(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        # Unconfirmed cancel: leave it for an operator, not retryable into a second prep.
        assert job.state == "prep_submitted"

    def test_staged_sibling_stays_required_in_config(self, dataset, mocks):
        # A previously-staged sibling must stay required so cleanup can't drop its staged data.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(
            dataset=sibling, state="prep_completed", prep_slurm_job_id="p", staged_at=timezone.now()
        )
        submit.submit_dataset_prep(dataset)
        assert mocks["required_ids"] == {2, 3}

    def test_failed_staged_sibling_stays_required(self, dataset, mocks):
        # A failed staged sibling still has a tree to protect.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="failed", prep_slurm_job_id="", staged_at=timezone.now())
        submit.submit_dataset_prep(dataset)
        assert mocks["required_ids"] == {2, 3}

    def test_push_inflight_sibling_is_required_before_staged_at(self, dataset, mocks):
        # A pushing sibling must stay protected in the shared config.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="push_running", push_slurm_job_id="x", staged_at=None)
        submit.submit_dataset_prep(dataset)
        assert mocks["required_ids"] == {2, 3}

    def test_unstaged_sibling_is_not_required(self, dataset, mocks):
        # A sibling that never staged and isn't in flight (failed, staged_at null) has no tree to protect.
        other = Dataset.objects.create(deposition=dataset.deposition, title="Other", dataset_id=4)
        DatasetJob.objects.create(dataset=other, state="failed", staged_at=None)
        submit.submit_dataset_prep(dataset)
        assert mocks["required_ids"] == {2}

    def test_lost_claim_before_id_recorded_cancels_orphan(self, dataset, mocks, monkeypatch):
        # If the id/staged_at write matches no row (claim lost), cancel the launched job, don't poll it.
        cancelled = {}
        monkeypatch.setattr(
            submit, "cancel_deposition_job", lambda *, cluster_id, job_id, auth: cancelled.update(id=job_id)
        )

        def launch_then_steal(*, processor_name, params, cluster_id, job_name, auth):
            DatasetJob.objects.filter(dataset=dataset).update(prep_slurm_job_id="other")  # clears our claim
            return "slurm-500"

        monkeypatch.setattr(submit, "launch_deposition_job", launch_then_steal)
        with pytest.raises(submit.LaunchError, match="Lost the prep claim"):
            submit.submit_dataset_prep(dataset)
        assert cancelled == {"id": "slurm-500"}
        assert mocks["synced"] is None  # poller never started


def _passed_validation(attempt):
    """A pre-flight result that clears require_validation for the given prep attempt."""
    return {"status": "passed", "attempt": attempt, "dataset_id": 2, "warnings": [], "blocking_issues": []}


@pytest.mark.parametrize(
    "phase,username,email,expected",
    [
        ("prep", "owner", "owner@example.org", "owner@example.org"),
        ("push", "owner", "owner@example.org", "owner@example.org"),
        ("prep", "owner@example.org", "", "owner@example.org"),
        ("prep", "owner", "owner@example.org\n#SBATCH --output=/tmp/injected", None),
    ],
)
def test_jobs_notify_the_owner_without_changing_service_account_auth(dataset, mocks, phase, username, email, expected):
    owner = User.objects.create_user(username=username, email=email)
    dataset.deposition.submitter_user = owner
    dataset.deposition.save(update_fields=["submitter_user"])
    if phase == "prep":
        submit.submit_dataset_prep(dataset)
    else:
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )
        submit.submit_dataset_push(dataset)
    launched = mocks["launched"]
    assert launched["params"].get("slurm_mail_user") == expected
    assert launched["auth"] is mocks["auth"]


@pytest.mark.django_db
class TestSubmitDatasetPush:
    def test_push_without_an_owner_uses_service_auth_and_omits_mail_recipient(self, dataset, mocks):
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )

        submit.submit_dataset_push(dataset)

        launched = mocks["launched"]
        assert launched["auth"] is mocks["auth"]  # service account
        assert set(launched["params"]) == {"staged_dir", "s3_dest"}

    def test_push_happy_path(self, dataset, mocks):
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )
        job = submit.submit_dataset_push(dataset)
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-500"
        launched = mocks["launched"]
        assert launched["processor"] == "deposition-push"
        assert launched["auth"] is mocks["auth"]
        staging_dir = resolve_dir("deposition_staging", cluster="cluster-a", deposition_id=1).rstrip("/")
        assert launched["params"]["staged_dir"] == f"{staging_dir}/2"
        assert launched["params"]["s3_dest"] == "s3://example-bucket/depositions/1/2"
        assert mocks["synced"] == (job.id, "push", "cluster-a", "slurm-500")

    def test_push_poller_start_failure_cancels_job_and_fails_row(self, dataset, mocks, monkeypatch):
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )
        cancelled = {}

        def boom(*a):
            raise RuntimeError("django-q is down")

        monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", boom)
        monkeypatch.setattr(
            submit,
            "cancel_deposition_job",
            lambda *, cluster_id, job_id, auth: cancelled.update(id=job_id, cluster=cluster_id, auth=auth),
        )
        with pytest.raises(RuntimeError):
            submit.submit_dataset_push(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        assert cancelled == {"id": "slurm-500", "cluster": "cluster-a", "auth": mocks["auth"]}

    def test_push_rejected_without_passed_validation(self, dataset, mocks):
        # Blocking issues keep the upload gated even though prep completed.
        DatasetJob.objects.create(
            dataset=dataset,
            state="prep_completed",
            prep_slurm_job_id="p1",
            validation={"status": "failed", "attempt": "p1", "warnings": [], "blocking_issues": [{"message": "x"}]},
        )
        with pytest.raises(SubmissionValidationError, match="validation"):
            submit.submit_dataset_push(dataset)
        assert mocks["launched"] is None

    def test_push_rejects_before_prep_completed(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_submitted", prep_slurm_job_id="p1")
        with pytest.raises(SubmissionValidationError, match="prep_completed"):
            submit.submit_dataset_push(dataset)
        assert mocks["launched"] is None

    def test_push_rejects_when_never_prepared(self, dataset, mocks):
        with pytest.raises(SubmissionValidationError, match="hasn't been prepared"):
            submit.submit_dataset_push(dataset)
        assert mocks["launched"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("cluster_override", [False, True])
def test_prep_and_push_use_same_configured_destination(dataset, mocks, cluster_override):
    destination = "s3://another-institution/depositions"
    kind = DataKind.objects.get(data_type="deposition_sync_destination")
    if cluster_override:
        cluster, _ = Cluster.objects.get_or_create(cluster_id="cluster-a")
        PathType.objects.create(data_kind=kind, cluster=cluster, overlay_path=destination + "/")
    else:
        PathType.objects.filter(data_kind=kind, cluster=None).update(overlay_path=destination + "/")

    job = submit.submit_dataset_prep(dataset)
    assert mocks["sync_destination"] == destination
    DatasetJob.objects.filter(pk=job.pk).update(state="prep_completed", validation=_passed_validation("slurm-500"))
    dataset.refresh_from_db()
    submit.submit_dataset_push(dataset)
    assert mocks["launched"]["params"]["s3_dest"] == destination + "/1/2"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "staging_template",
    [
        "/shared/service-user/depositions/{deposition_id}/",
        "/srv/portal/staging/{deposition_id}/",
    ],
)
def test_prep_and_push_use_configured_cluster_staging_path(dataset, mocks, staging_template):
    kind = DataKind.objects.get(data_type="deposition_staging")
    cluster = Cluster.objects.get(cluster_id="cluster-a")
    PathType.objects.update_or_create(data_kind=kind, cluster=cluster, defaults={"overlay_path": staging_template})
    output_dir = staging_template.format(deposition_id=dataset.deposition.deposition_id).rstrip("/")

    job = submit.submit_dataset_prep(dataset)
    assert mocks["launched"]["params"]["output_dir"] == output_dir + "/"
    assert mocks["launched"]["params"]["config_path"] == output_dir + "/dataprep_config.yaml"
    destination = mocks["sync_destination"]
    DatasetJob.objects.filter(pk=job.pk).update(state="prep_completed", validation=_passed_validation("slurm-500"))
    dataset.refresh_from_db()

    submit.submit_dataset_push(dataset)
    assert mocks["launched"]["params"]["staged_dir"] == output_dir + f"/{dataset.dataset_id}"
    assert mocks["launched"]["params"]["s3_dest"] == destination + f"/1/{dataset.dataset_id}"


@pytest.mark.django_db
def test_push_rejects_invalid_configured_destination(dataset, mocks):
    PathType.objects.filter(data_kind__data_type="deposition_sync_destination", cluster=None).update(
        overlay_path="/not-s3"
    )
    DatasetJob.objects.create(
        dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
    )
    with pytest.raises(SubmissionValidationError, match="S3 destination"):
        submit.submit_dataset_push(dataset)
    assert mocks["launched"] is None
    assert DatasetJob.objects.get(dataset=dataset).state == "prep_completed"


@pytest.mark.django_db
@pytest.mark.parametrize("phase", ["prep", "push"])
def test_runs_as_the_service_account(dataset, mocks, phase):
    # Deposition jobs use the configured service credentials.
    if phase == "push":
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )
    getattr(submit, f"submit_dataset_{phase}")(dataset)
    assert mocks["launched"]["auth"] is mocks["auth"]


@pytest.mark.django_db
@pytest.mark.parametrize("phase", ["prep", "push"])
def test_missing_service_credentials_does_not_claim_or_launch(dataset, mocks, monkeypatch, phase):
    # Auth resolves before the job is claimed/launched, so a missing service key strands nothing.
    monkeypatch.setattr(submit.clusterio, "get_auth_service_user", _raise_no_creds)
    if phase == "push":
        DatasetJob.objects.create(
            dataset=dataset, state="prep_completed", prep_slurm_job_id="p1", validation=_passed_validation("p1")
        )
    with pytest.raises(SubmissionValidationError, match="isn't configured"):
        getattr(submit, f"submit_dataset_{phase}")(dataset)
    assert mocks["launched"] is None
    job = DatasetJob.objects.filter(dataset=dataset).first()
    # Prep never created a row; push left the prepared one untouched (not stranded mid-submit).
    assert (job.state if job else None) == (None if phase == "prep" else "prep_completed")


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["prep_submitted", "prep_running"])
@pytest.mark.parametrize("staged", [False, True])
def test_sibling_prep_blocks_submission_before_config_is_frozen(dataset, mocks, state, staged):
    sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sibling", dataset_id=3)
    DatasetJob.objects.create(
        dataset=sibling, state=state, staged_at=timezone.now() if staged else None, prep_slurm_job_id=""
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(dataset)
    assert mocks["launched"] is None
    assert mocks["required_ids"] is None
    assert not DatasetJob.objects.filter(dataset=dataset).exists()


@pytest.mark.django_db
def test_second_dataset_waits_for_first_prep_then_config_includes_both(dataset, mocks, monkeypatch):
    monkeypatch.setattr(submit, "dataprep_config_yaml", dataprep_config_yaml)
    first_job = submit.submit_dataset_prep(dataset)
    first_launch = mocks["launched"]
    assert set(yaml.safe_load(first_launch["params"]["config_yaml"])["datasets"]) == {"dataset_2"}
    second = Dataset.objects.create(
        deposition=dataset.deposition, title="B", description="Reviewed sibling", sample=dataset.sample, dataset_id=3
    )
    session = DepositionSession.objects.create(dataset=second, msi_session=dataset.sessions.get().msi_session)
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/b"}, "acquisition": {}}
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(second)
    assert mocks["launched"] is first_launch
    on_prep_complete(first_job, True, job_id=first_job.prep_slurm_job_id)
    submit.submit_dataset_prep(second)
    config = yaml.safe_load(mocks["launched"]["params"]["config_yaml"])
    assert set(config["datasets"]) == {"dataset_2", "dataset_3"}
    assert config["datasets"]["dataset_2"]["sessions"]
    assert config["datasets"]["dataset_3"]["sessions"]


@pytest.mark.django_db
def test_active_prep_in_another_deposition_does_not_block(dataset, mocks):
    other_dep = Deposition.objects.create(title="Other", deposition_id=10)
    other_ds = Dataset.objects.create(deposition=other_dep, title="Other", dataset_id=20)
    DatasetJob.objects.create(dataset=other_ds, state="prep_submitted")
    assert submit.submit_dataset_prep(dataset).state == "prep_submitted"


@pytest.mark.django_db
def test_unconfirmed_cancellation_keeps_deposition_blocked(dataset, mocks, monkeypatch):
    def unavailable(*args):
        raise RuntimeError("poller unavailable")

    def cannot_cancel(**kwargs):
        raise OSError("cancellation not confirmed")

    monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", unavailable)
    monkeypatch.setattr(submit, "cancel_deposition_job", cannot_cancel)
    with pytest.raises(OSError, match="cancellation not confirmed"):
        submit.submit_dataset_prep(dataset)
    first_launch = mocks["launched"]
    second = Dataset.objects.create(deposition=dataset.deposition, title="Sibling", dataset_id=3)
    session = DepositionSession.objects.create(dataset=second, msi_session=dataset.sessions.get().msi_session)
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/b"}, "acquisition": {}}
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(second)
    assert mocks["launched"] is first_launch
    assert DatasetJob.objects.get(dataset=dataset).state == "prep_submitted"


@pytest.mark.django_db
class TestPreviewConfigYaml:
    """Download must be the file submit would upload: this dataset + staged siblings required."""

    def test_marks_this_dataset_and_staged_siblings_required(self, dataset, mocks):
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="pending", staged_at=timezone.now())
        assert submit.preview_config_yaml(dataset) == "yaml-text"
        assert mocks["required_ids"] == {2, 3}

    def test_includes_this_dataset_even_with_no_siblings(self, dataset, mocks):
        submit.preview_config_yaml(dataset)
        assert mocks["required_ids"] == {2}

    def test_editable_job_previews_the_resubmit_cluster_not_the_stale_stored_one(self, dataset, mocks, monkeypatch):
        # A failed job's stored cluster can be stale; preview must derive it like a resubmit would.
        DatasetJob.objects.create(dataset=dataset, state="failed", cluster_id="stale-cluster")
        seen = {}
        monkeypatch.setattr(submit, "resolve_dir", lambda *a, cluster, **k: seen.update(cluster=cluster) or "/staged")
        monkeypatch.setattr(submit, "resolve_sync_destination", lambda *, cluster: "s3://x")
        submit.preview_config_yaml(dataset)
        assert seen["cluster"] == "cluster-a"  # derived via _cluster_for_dataset, not "stale-cluster"

    def test_locked_job_previews_the_staged_cluster(self, dataset, mocks, monkeypatch):
        DatasetJob.objects.create(dataset=dataset, state="prep_running", cluster_id="staged-cluster")
        seen = {}
        monkeypatch.setattr(submit, "resolve_dir", lambda *a, cluster, **k: seen.update(cluster=cluster) or "/staged")
        monkeypatch.setattr(submit, "resolve_sync_destination", lambda *, cluster: "s3://x")
        submit.preview_config_yaml(dataset)
        assert seen["cluster"] == "staged-cluster"  # locked → show what was actually staged

    def test_rejects_unreserved_ids(self, dataset, mocks):
        dataset.dataset_id = None
        with pytest.raises(SubmissionValidationError, match="Reserve"):
            submit.preview_config_yaml(dataset)


@pytest.mark.django_db
def test_prepared_dataset_can_retry_once_and_drops_stale_validation(dataset, mocks):
    DatasetJob.objects.create(
        dataset=dataset,
        state="prep_completed",
        prep_slurm_job_id="old",
        validation=_passed_validation("old"),
        staged_at=timezone.now(),
    )
    job = submit.submit_dataset_prep(dataset)
    assert job.state == "prep_submitted" and job.validation is None
    assert job.prep_slurm_job_id == "slurm-500"
    with pytest.raises(SubmissionValidationError, match="already"):
        submit.submit_dataset_prep(dataset)


@pytest.mark.django_db
@pytest.mark.parametrize("new_cluster,new_attempt", [("cluster-b", "new"), ("cluster-a", "new"), ("cluster-b", "old")])
def test_push_refuses_changed_prep_snapshot(dataset, mocks, monkeypatch, new_cluster, new_attempt):
    job = DatasetJob.objects.create(
        dataset=dataset,
        state="prep_completed",
        cluster_id="cluster-a",
        prep_slurm_job_id="old",
        validation=_passed_validation("old"),
    )

    def auth_after_preparation_changed():
        # Another request resets/re-prepares while this request still holds old launch paths.
        DatasetJob.objects.filter(pk=job.pk).update(
            cluster_id=new_cluster, prep_slurm_job_id=new_attempt, validation=_passed_validation(new_attempt)
        )
        return mocks["auth"]

    monkeypatch.setattr(submit, "_service_auth", auth_after_preparation_changed)
    with pytest.raises(SubmissionValidationError, match="Preparation changed"):
        submit.submit_dataset_push(dataset)
    job.refresh_from_db()
    assert job.state == "prep_completed"
    assert job.prep_slurm_job_id == new_attempt and job.cluster_id == new_cluster
    assert mocks["launched"] is None and mocks["synced"] is None
