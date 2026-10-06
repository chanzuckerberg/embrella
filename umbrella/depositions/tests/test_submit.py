"""Tests for the dataset submit orchestration."""

import pytest
from django.utils import timezone

from depositions.models import (
    Dataset,
    DatasetJob,
    Deposition,
    DepositionAnnotation,
    DepositionSession,
    TiltseriesMetadata,
)
from depositions.services import submit


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

    def launch(*, processor_name, params, cluster_id, job_name):
        calls["launched"] = {"processor": processor_name, "params": params, "cluster": cluster_id, "job_name": job_name}
        return "slurm-500"

    monkeypatch.setattr(submit, "cluster_id_for_run", lambda *a, **k: "bruno")
    monkeypatch.setattr(submit.clusterio, "ensure_remote_dir", lambda *a: calls.__setitem__("mkdir", a))
    monkeypatch.setattr(submit.clusterio, "write_remote_file_atomic", write)

    def config_yaml(deposition, *, output_dir, required_dataset_ids=None):
        calls["required_ids"] = required_dataset_ids
        return "yaml-text"

    monkeypatch.setattr(submit, "dataprep_config_yaml", config_yaml)
    monkeypatch.setattr(submit, "launch_deposition_job", launch)
    monkeypatch.setattr(submit.tasks, "start_deposition_job_syncer", lambda *a: calls.__setitem__("synced", a))
    return calls


@pytest.mark.django_db
class TestSubmitDatasetPrep:
    def test_happy_path(self, dataset, mocks, test_msi_session):
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert job.prep_slurm_job_id == "slurm-500"
        dataset.refresh_from_db()
        assert dataset.status == "syncing"
        # Config written to the seeded staging path for this deposition id.
        assert mocks["written"][:2] == ("bruno", "/hpc/projects/group.czii/depositions/1/dataprep_config.yaml")
        # Prep scoped to this dataset's sessions, whole-config validate skipped.
        launched = mocks["launched"]
        assert launched["params"]["session_names"] == [test_msi_session.name]
        assert launched["params"]["run_validate"] is False
        assert launched["job_name"] == "deposition_prep_1_2"
        # Staging dir created before the config write; poller bound to this attempt's id.
        assert mocks["mkdir"] == ("bruno", "/hpc/projects/group.czii/depositions/1/")
        assert mocks["synced"] == (job.id, "prep", "bruno", "slurm-500")

    def test_rejects_unreserved_ids(self, dataset, mocks):
        dataset.dataset_id = None  # checked on the passed object
        with pytest.raises(ValueError, match="Reserve"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_rejects_resubmit_while_in_flight(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_running", prep_slurm_job_id="old")
        with pytest.raises(ValueError, match="already"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_rejects_selected_annotations_until_supported(self, dataset, mocks):
        session = dataset.sessions.get()
        DepositionAnnotation.objects.create(session=session, copick_kind="picks", copick_ref="ribosome-0")
        with pytest.raises(ValueError, match="annotations isn't supported"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

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
        with pytest.raises(ValueError, match="ready to submit"):
            submit.submit_dataset_prep(dataset)
        assert mocks["launched"] is None

    def test_retry_after_failure(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="failed", error_message="boom")
        job = submit.submit_dataset_prep(dataset)
        assert job.state == "prep_submitted"
        assert not job.error_message

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
            lambda *, cluster_id, job_id: cancelled.update(id=job_id, cluster=cluster_id),
        )
        with pytest.raises(RuntimeError):
            submit.submit_dataset_prep(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        # The job reached the cluster, so it must be cancelled rather than left running unwatched.
        assert cancelled == {"id": "slurm-500", "cluster": "bruno"}

    def test_poller_start_failure_leaves_row_if_cancel_fails(self, dataset, mocks, monkeypatch):
        def boom(*a):
            raise RuntimeError("django-q is down")

        def bad_cancel(*, cluster_id, job_id):
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

    def test_staged_sibling_mid_retry_stays_required(self, dataset, mocks):
        # A re-claim blanks prep_slurm_job_id; staged_at must keep the staged tree protected.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(
            dataset=sibling, state="prep_submitted", prep_slurm_job_id="", staged_at=timezone.now()
        )
        submit.submit_dataset_prep(dataset)
        assert mocks["required_ids"] == {2, 3}

    def test_inflight_sibling_is_required_before_staged_at(self, dataset, mocks):
        # A sibling mid-first-submit (locked state, staged_at not yet set) must still be required.
        sibling = Dataset.objects.create(deposition=dataset.deposition, title="Sib", dataset_id=3)
        DatasetJob.objects.create(dataset=sibling, state="prep_submitted", prep_slurm_job_id="x", staged_at=None)
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
        monkeypatch.setattr(submit, "cancel_deposition_job", lambda *, cluster_id, job_id: cancelled.update(id=job_id))

        def launch_then_steal(*, processor_name, params, cluster_id, job_name):
            DatasetJob.objects.filter(dataset=dataset).update(prep_slurm_job_id="other")  # clears our claim
            return "slurm-500"

        monkeypatch.setattr(submit, "launch_deposition_job", launch_then_steal)
        with pytest.raises(ValueError, match="Lost the prep claim"):
            submit.submit_dataset_prep(dataset)
        assert cancelled == {"id": "slurm-500"}
        assert mocks["synced"] is None  # poller never started


@pytest.mark.django_db
class TestSubmitDatasetPush:
    def test_push_happy_path(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_completed", prep_slurm_job_id="p1")
        job = submit.submit_dataset_push(dataset)
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-500"
        launched = mocks["launched"]
        assert launched["processor"] == "deposition-push"
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
            lambda *, cluster_id, job_id: cancelled.update(id=job_id, cluster=cluster_id),
        )
        with pytest.raises(RuntimeError):
            submit.submit_dataset_push(dataset)
        job = DatasetJob.objects.get(dataset=dataset)
        assert job.state == "failed"
        assert cancelled == {"id": "slurm-500", "cluster": "bruno"}

    def test_push_rejects_before_prep_completed(self, dataset, mocks):
        DatasetJob.objects.create(dataset=dataset, state="prep_submitted", prep_slurm_job_id="p1")
        with pytest.raises(ValueError, match="prep_completed"):
            submit.submit_dataset_push(dataset)
        assert mocks["launched"] is None

    def test_push_rejects_when_never_prepared(self, dataset, mocks):
        with pytest.raises(ValueError, match="hasn't been prepared"):
            submit.submit_dataset_push(dataset)
        assert mocks["launched"] is None
