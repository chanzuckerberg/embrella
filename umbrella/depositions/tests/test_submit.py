"""Tests for the dataset submit orchestration."""

from types import SimpleNamespace

import pytest
import yaml
from accounts.cluster_usernames import MissingClusterCredentialsError
from django.utils import timezone
from stores.models import Cluster, DataKind, PathType

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


@pytest.fixture
def dataset(db, test_msi_session):
    deposition = Deposition.objects.create(title="Dep", deposition_id=1)
    ds = Dataset.objects.create(deposition=deposition, title="DS", dataset_id=2)
    session = DepositionSession.objects.create(dataset=ds, msi_session=test_msi_session, aretomo_run_name="run001")
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/a"}, "acquisition": {}}
    )
    return ds


@pytest.fixture
def mocks(monkeypatch):
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

    calls["user"] = SimpleNamespace(pk=1)
    calls["auth"] = {"username": "cluster-alice", "pkey": "test-key"}
    monkeypatch.setattr(submit.clusterio, "get_auth_for_user", lambda user, cluster: (calls["auth"], None))
    monkeypatch.setattr(submit, "cluster_id_for_run", lambda *a, **k: "bruno")
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
    def test_happy_path(self, dataset, mocks, test_msi_session):
        job = submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert job.state == "prep_submitted"
        assert job.prep_slurm_job_id == "slurm-500"
        dataset.refresh_from_db()
        assert dataset.status == "syncing"
        assert mocks["written"] is None
        assert "mkdir" not in mocks
        # Prep scoped to this dataset's sessions, whole-config validate skipped.
        launched = mocks["launched"]
        assert launched["params"]["session_names"] == [test_msi_session.name]
        assert launched["params"]["run_validate"] is False
        assert launched["job_name"] == "deposition_prep_1_2"
        assert launched["params"]["config_yaml"] == "yaml-text"
        assert launched["params"]["config_path"] == "/hpc/projects/group.czii/depositions/1/dataprep_config.yaml"
        assert launched["auth"] is mocks["auth"]
        assert mocks["synced"] == (job.id, "prep", "bruno", "slurm-500")

    def test_rejects_unreserved_ids(self, dataset, mocks):
        dataset.dataset_id = None  # checked on the passed object
        with pytest.raises(SubmissionValidationError, match="Reserve"):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["launched"] is None

    def test_rejects_resubmit_while_in_flight(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_running", prep_slurm_job_id="old")
        with pytest.raises(SubmissionValidationError, match="already"):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["launched"] is None

    def test_rejects_selected_annotations_until_supported(self, dataset, mocks):
        session = dataset.sessions.get()
        DepositionAnnotation.objects.create(session=session, copick_kind="picks", copick_ref="ribosome-0")
        with pytest.raises(SubmissionValidationError, match="annotations isn't supported"):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["launched"] is None

    def test_deselected_annotations_do_not_block(self, dataset, mocks):
        session = dataset.sessions.get()
        DepositionAnnotation.objects.create(
            session=session, copick_kind="picks", copick_ref="ribosome-0", is_selected=False
        )
        job = submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert job.state == "prep_submitted"
        assert mocks["launched"] is not None

    def test_rejects_not_ready_dataset(self, dataset, mocks):
        TiltseriesMetadata.objects.filter(session__dataset=dataset).delete()
        with pytest.raises(SubmissionValidationError, match="ready to submit"):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["launched"] is None

    def test_retry_after_failure(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="failed", error_message="boom")
        job = submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert job.state == "prep_submitted"
        assert not job.error_message

    def test_path_resolution_failure_fails_row_without_launching(self, dataset, mocks, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("no deposition_staging PathType")

        monkeypatch.setattr(submit, "resolve_dir", boom)
        with pytest.raises(RuntimeError):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
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
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        # The job reached the cluster, so it must be cancelled rather than left running unwatched.
        assert cancelled == {"id": "slurm-500", "cluster": "bruno", "auth": mocks["auth"]}

    def test_poller_start_failure_leaves_row_if_cancel_fails(self, dataset, mocks, monkeypatch):
        def boom(*a):
            raise RuntimeError("django-q is down")

        def bad_cancel(*, cluster_id, job_id, auth):
            raise OSError("scancel failed")

        monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", boom)
        monkeypatch.setattr(submit, "cancel_deposition_job", bad_cancel)
        with pytest.raises(OSError, match="scancel failed"):
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        job = DatasetJob.objects.get(dataset=dataset)
        # Unconfirmed cancel: leave it for an operator, not retryable into a second prep.
        assert job.state == "prep_submitted"

    def test_staged_sibling_stays_required_in_config(self, dataset, mocks):
        # A previously-staged sibling must stay required so cleanup can't drop its staged data.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(
            dataset=sibling, state="prep_completed", prep_slurm_job_id="p", staged_at=timezone.now()
        )
        submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["required_ids"] == {2, 3}

    def test_failed_staged_sibling_stays_required(self, dataset, mocks):
        # A failed staged sibling still has a tree to protect.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="failed", prep_slurm_job_id="", staged_at=timezone.now())
        submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["required_ids"] == {2, 3}

    def test_push_inflight_sibling_is_required_before_staged_at(self, dataset, mocks):
        # A pushing sibling must stay protected in the shared config.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="push_running", push_slurm_job_id="x", staged_at=None)
        submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert mocks["required_ids"] == {2, 3}

    def test_unstaged_sibling_is_not_required(self, dataset, mocks):
        # A sibling that never staged and isn't in flight (failed, staged_at null) has no tree to protect.
        other = Dataset.objects.create(deposition=dataset.deposition, title="Other", dataset_id=4)
        DatasetJob.objects.create(dataset=other, state="failed", staged_at=None)
        submit.submit_dataset_prep(dataset, user=mocks["user"])
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
            submit.submit_dataset_prep(dataset, user=mocks["user"])
        assert cancelled == {"id": "slurm-500"}
        assert mocks["synced"] is None  # poller never started


@pytest.mark.django_db
class TestSubmitDatasetPush:
    def test_push_happy_path(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_completed", prep_slurm_job_id="p1")
        job = submit.submit_dataset_push(dataset, user=mocks["user"])
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-500"
        launched = mocks["launched"]
        assert launched["processor"] == "deposition-push"
        assert launched["auth"] is mocks["auth"]
        assert launched["params"]["staged_dir"] == "/hpc/projects/group.czii/depositions/1/2"
        assert launched["params"]["s3_dest"] == "s3://cryoetportal-biohub-hpc-globus/CZII/1/2"
        assert mocks["synced"] == (job.id, "push", "bruno", "slurm-500")

    def test_push_poller_start_failure_cancels_job_and_fails_row(self, dataset, mocks, monkeypatch):
        DatasetJob.objects.create(dataset=dataset, state="prep_completed", prep_slurm_job_id="p1")
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
            submit.submit_dataset_push(dataset, user=mocks["user"])
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        assert cancelled == {"id": "slurm-500", "cluster": "bruno", "auth": mocks["auth"]}

    def test_push_rejects_before_prep_completed(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_submitted", prep_slurm_job_id="p1")
        with pytest.raises(SubmissionValidationError, match="prep_completed"):
            submit.submit_dataset_push(dataset, user=mocks["user"])
        assert mocks["launched"] is None

    def test_push_rejects_when_never_prepared(self, dataset, mocks):
        with pytest.raises(SubmissionValidationError, match="hasn't been prepared"):
            submit.submit_dataset_push(dataset, user=mocks["user"])
        assert mocks["launched"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("cluster_override", [False, True])
def test_prep_and_push_use_same_configured_destination(dataset, mocks, cluster_override):
    destination = "s3://another-institution/depositions"
    kind = DataKind.objects.get(data_type="deposition_sync_destination")
    if cluster_override:
        cluster, _ = Cluster.objects.get_or_create(cluster_id="bruno")
        PathType.objects.create(data_kind=kind, cluster=cluster, overlay_path=destination + "/")
    else:
        PathType.objects.filter(data_kind=kind, cluster=None).update(overlay_path=destination + "/")

    job = submit.submit_dataset_prep(dataset, user=mocks["user"])
    assert mocks["sync_destination"] == destination
    DatasetJob.objects.filter(pk=job.pk).update(state="prep_completed")
    dataset.refresh_from_db()
    submit.submit_dataset_push(dataset, user=mocks["user"])
    assert mocks["launched"]["params"]["s3_dest"] == destination + "/1/2"


@pytest.mark.django_db
def test_push_rejects_invalid_configured_destination(dataset, mocks):
    PathType.objects.filter(data_kind__data_type="deposition_sync_destination", cluster=None).update(
        overlay_path="/not-s3"
    )
    DatasetJob.objects.create(dataset=dataset, state="prep_completed", prep_slurm_job_id="p1")
    with pytest.raises(SubmissionValidationError, match="S3 destination"):
        submit.submit_dataset_push(dataset, user=mocks["user"])
    assert mocks["launched"] is None
    assert DatasetJob.objects.get(dataset=dataset).state == "prep_completed"


@pytest.mark.django_db
@pytest.mark.parametrize("phase", ["prep", "push"])
def test_missing_credentials_does_not_claim_or_launch(dataset, mocks, monkeypatch, phase):
    if phase == "push":
        DatasetJob.objects.create(dataset=dataset, state="prep_completed", cluster_id="bruno")

    def missing(user, cluster_id):
        assert user is mocks["user"]
        assert cluster_id == "bruno"
        raise MissingClusterCredentialsError(user.pk, cluster_id)

    monkeypatch.setattr(submit.clusterio, "get_auth_for_user", missing)
    with pytest.raises(MissingClusterCredentialsError):
        getattr(submit, f"submit_dataset_{phase}")(dataset, user=mocks["user"])
    assert mocks["launched"] is None
    if phase == "prep":
        assert not DatasetJob.objects.filter(dataset=dataset).exists()
    else:
        assert DatasetJob.objects.get(dataset=dataset).state == "prep_completed"


@pytest.mark.django_db
def test_invalid_cluster_auth_never_falls_back_to_service_account(dataset, mocks, monkeypatch):
    monkeypatch.setattr(submit.clusterio, "get_auth_for_user", lambda *args: (None, {"error": "invalid cluster"}))
    with pytest.raises(SubmissionValidationError, match="cluster is unavailable"):
        submit.submit_dataset_prep(dataset, user=mocks["user"])
    assert mocks["launched"] is None
    assert not DatasetJob.objects.filter(dataset=dataset).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["prep_submitted", "prep_running"])
@pytest.mark.parametrize("staged", [False, True])
def test_sibling_prep_blocks_submission_before_config_is_frozen(dataset, mocks, state, staged):
    sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sibling", dataset_id=3)
    DatasetJob.objects.create(
        dataset=sibling, state=state, staged_at=timezone.now() if staged else None, prep_slurm_job_id=""
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(dataset, user=mocks["user"])
    assert mocks["launched"] is None
    assert mocks["required_ids"] is None
    assert not DatasetJob.objects.filter(dataset=dataset).exists()


@pytest.mark.django_db
def test_second_dataset_waits_for_first_prep_then_config_includes_both(dataset, mocks, monkeypatch):
    monkeypatch.setattr(submit, "dataprep_config_yaml", dataprep_config_yaml)
    first_job = submit.submit_dataset_prep(dataset, user=mocks["user"])
    first_launch = mocks["launched"]
    assert set(yaml.safe_load(first_launch["params"]["config_yaml"])["datasets"]) == {"dataset_2"}
    second = Dataset.objects.create(deposition=dataset.deposition, title="B", dataset_id=3)
    session = DepositionSession.objects.create(dataset=second, msi_session=dataset.sessions.get().msi_session)
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/b"}, "acquisition": {}}
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(second, user=mocks["user"])
    assert mocks["launched"] is first_launch
    on_prep_complete(first_job, True, job_id=first_job.prep_slurm_job_id)
    submit.submit_dataset_prep(second, user=mocks["user"])
    config = yaml.safe_load(mocks["launched"]["params"]["config_yaml"])
    assert set(config["datasets"]) == {"dataset_2", "dataset_3"}
    assert config["datasets"]["dataset_2"]["sessions"]
    assert config["datasets"]["dataset_3"]["sessions"]


@pytest.mark.django_db
def test_active_prep_in_another_deposition_does_not_block(dataset, mocks):
    other_dep = Deposition.objects.create(title="Other", deposition_id=10)
    other_ds = Dataset.objects.create(deposition=other_dep, title="Other", dataset_id=20)
    DatasetJob.objects.create(dataset=other_ds, state="prep_submitted")
    assert submit.submit_dataset_prep(dataset, user=mocks["user"]).state == "prep_submitted"


@pytest.mark.django_db
def test_unconfirmed_cancellation_keeps_deposition_blocked(dataset, mocks, monkeypatch):
    def unavailable(*args):
        raise RuntimeError("poller unavailable")

    def cannot_cancel(**kwargs):
        raise OSError("cancellation not confirmed")

    monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", unavailable)
    monkeypatch.setattr(submit, "cancel_deposition_job", cannot_cancel)
    with pytest.raises(OSError, match="cancellation not confirmed"):
        submit.submit_dataset_prep(dataset, user=mocks["user"])
    first_launch = mocks["launched"]
    second = Dataset.objects.create(deposition=dataset.deposition, title="Sibling", dataset_id=3)
    session = DepositionSession.objects.create(dataset=second, msi_session=dataset.sessions.get().msi_session)
    TiltseriesMetadata.objects.create(
        session=session, autofill_metadata={"paths": {"aretomo3": "/b"}, "acquisition": {}}
    )
    with pytest.raises(SubmissionValidationError, match="queued or running prep"):
        submit.submit_dataset_prep(second, user=mocks["user"])
    assert mocks["launched"] is first_launch
    assert DatasetJob.objects.get(dataset=dataset).state == "prep_submitted"
