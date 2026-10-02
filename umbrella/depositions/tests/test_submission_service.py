"""Tests for the DatasetJob submission-chaining service."""

import pytest
from django.db.models.query import QuerySet
from django.utils import timezone

from depositions.models import Dataset, DatasetJob, Deposition
from depositions.services import submission


def _job(state):
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    return DatasetJob.objects.create(
        dataset=ds, state=state, push_slurm_job_id="slurm-push" if state in submission.PUSH_ACTIVE else ""
    )


@pytest.mark.django_db
class TestOnPrepComplete:
    def test_success_advances_to_prep_completed(self):
        job = _job("prep_running")
        submission.on_prep_complete(job, True)
        job.refresh_from_db()
        assert job.state == "prep_completed"
        assert not job.error_message
        assert job.completed_at is None  # prep done != submission done

    def test_failure_marks_failed_with_error_and_timestamp(self):
        job = _job("prep_running")
        submission.on_prep_complete(job, False, error_message="sync blew up")
        job.refresh_from_db()
        assert job.state == "failed"
        assert job.error_message == "sync blew up"
        assert job.completed_at is not None

    def test_works_when_prep_skipped_running_state(self):
        job = _job("prep_submitted")
        submission.on_prep_complete(job, True)
        job.refresh_from_db()
        assert job.state == "prep_completed"

    def test_success_clears_a_prior_failure(self):
        job = _job("prep_running")
        job.error_message = "earlier prep failure"
        job.completed_at = timezone.now()
        job.save()
        submission.on_prep_complete(job, True)
        job.refresh_from_db()
        assert job.state == "prep_completed"
        assert not job.error_message
        assert job.completed_at is None

    def test_stale_prep_callback_does_not_fail_an_active_push(self):
        job = _job("push_running")
        submission.on_prep_complete(job, False, error_message="late prep error")
        job.refresh_from_db()
        assert job.state == "push_running"  # untouched
        assert not job.error_message

    def test_callback_from_superseded_attempt_is_ignored(self):
        job = _job("prep_running")
        job.prep_slurm_job_id = "slurm-new"
        job.save()
        submission.on_prep_complete(job, False, job_id="slurm-old")
        job.refresh_from_db()
        assert job.state == "prep_running"

    def test_stale_prep_instance_does_not_roll_back_a_claimed_push(self):
        # Syncer holds a prep_running copy; meanwhile prep finished and push was claimed.
        job = _job("prep_running")
        stale = DatasetJob.objects.get(pk=job.pk)  # caller's stale in-memory copy
        submission.on_prep_complete(DatasetJob.objects.get(pk=job.pk), True)
        submission.start_push(DatasetJob.objects.get(pk=job.pk), launch=lambda j: "slurm-push")
        returned = submission.on_prep_complete(stale, True)  # late callback on the stale copy
        assert returned is stale
        assert returned.state == "push_submitted"
        assert returned.push_slurm_job_id == "slurm-push"
        job.refresh_from_db()
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-push"

    def test_success_clears_stale_log_excerpt(self):
        job = _job("prep_running")
        job.log_excerpt = "traceback from failed attempt"
        job.save()
        submission.on_prep_complete(job, True)
        job.refresh_from_db()
        assert not job.log_excerpt


@pytest.mark.django_db
class TestStartPush:
    def test_launches_and_advances_to_push_submitted(self):
        job = _job("prep_completed")
        submission.start_push(job, launch=lambda j: "slurm-42")
        job.refresh_from_db()
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-42"

    def test_launch_receives_the_job(self):
        job = _job("prep_completed")
        seen = []

        def launch(j):
            seen.append(j)
            return "slurm-7"

        submission.start_push(job, launch=launch)
        assert seen == [job]

    def test_clears_stale_completion_metadata_on_relaunch(self):
        job = _job("prep_completed")
        job.error_message = "earlier failure"
        job.completed_at = timezone.now()
        job.save()
        submission.start_push(job, launch=lambda j: "slurm-1")
        job.refresh_from_db()
        assert not job.error_message
        assert job.completed_at is None

    def test_rejects_wrong_state_and_does_not_launch(self):
        job = _job("pending")
        launched = []
        with pytest.raises(ValueError):
            submission.start_push(job, launch=lambda j: launched.append(j) or "x")
        job.refresh_from_db()
        assert job.state == "pending"
        assert launched == []

    def test_second_submit_does_not_double_launch(self):
        job = _job("prep_completed")
        calls = []
        submission.start_push(job, launch=lambda j: calls.append(j) or "slurm-1")
        # Row is now push_submitted; a second Submit click must not launch again.
        with pytest.raises(ValueError):
            submission.start_push(job, launch=lambda j: calls.append(j) or "slurm-2")
        assert len(calls) == 1

    def test_launch_failure_marks_job_failed(self):
        job = _job("prep_completed")

        def boom(j):
            raise RuntimeError("sbatch unavailable")

        with pytest.raises(RuntimeError):
            submission.start_push(job, launch=boom)
        job.refresh_from_db()
        assert job.state == "failed"
        assert not job.push_slurm_job_id  # not left in push_submitted with no id
        assert job.dataset.status == "failed"

    @pytest.mark.parametrize("success", [True, False])
    @pytest.mark.parametrize("callback_id", [None, "", "slurm-push"])
    def test_completion_during_launch_is_ignored(self, success, callback_id):
        job = _job("prep_completed")

        def launch(j):
            submission.on_push_complete(j, success, job_id=callback_id)
            assert j.state == "push_submitted"
            assert j.push_slurm_job_id == ""
            assert j.dataset.status == "syncing"
            return "slurm-push"

        submission.start_push(job, launch=launch)
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == "slurm-push"
        submission.on_push_complete(job, success, job_id="slurm-push")
        assert job.state == ("completed" if success else "failed")

    @pytest.mark.parametrize("new_state", ["completed", "failed", "push_running"])
    @pytest.mark.parametrize("launch_fails", [True, False])
    def test_launch_result_does_not_overwrite_newer_state(self, new_state, launch_fails):
        job = _job("prep_completed")

        def launch(j):
            DatasetJob.objects.filter(pk=j.pk).update(state=new_state, error_message="newer state")
            if launch_fails:
                raise RuntimeError("sbatch unavailable")
            return "slurm-push"

        if launch_fails:
            with pytest.raises(RuntimeError, match="sbatch unavailable"):
                submission.start_push(job, launch=launch)
        else:
            submission.start_push(job, launch=launch)
        job.refresh_from_db()
        assert job.state == new_state
        assert job.error_message == "newer state"
        assert job.push_slurm_job_id == ""

    @pytest.mark.parametrize("empty_id", [None, ""])
    def test_empty_launch_id_marks_job_failed(self, empty_id):
        job = _job("prep_completed")
        with pytest.raises(ValueError, match="empty SLURM job id"):
            submission.start_push(job, launch=lambda j: empty_id)
        job.refresh_from_db()
        assert job.state == "failed"
        assert not job.push_slurm_job_id
        assert job.completed_at is not None
        job.dataset.refresh_from_db()
        assert job.dataset.status == "failed"

    def test_id_persistence_failure_leaves_claim_intact(self, monkeypatch):
        job = _job("prep_completed")
        original_update = QuerySet.update

        def fail_id_update(qs, **fields):
            if set(fields) == {"push_slurm_job_id", "updated_at"}:
                raise RuntimeError("id save failed")
            return original_update(qs, **fields)

        monkeypatch.setattr(QuerySet, "update", fail_id_update)
        with pytest.raises(RuntimeError, match="id save failed"):
            submission.start_push(job, launch=lambda j: "slurm-push")
        job.refresh_from_db()
        assert job.state == "push_submitted"
        assert job.push_slurm_job_id == ""
        assert not job.error_message


@pytest.mark.django_db
class TestOnPushComplete:
    @pytest.mark.parametrize("state", submission.PUSH_ACTIVE)
    @pytest.mark.parametrize("missing_id", [None, ""])
    @pytest.mark.parametrize("success", [True, False])
    def test_completion_requires_a_persisted_id(self, state, missing_id, success):
        job = _job(state)
        job.push_slurm_job_id = missing_id
        job.save()
        submission.on_push_complete(job, success)
        job.refresh_from_db()
        assert job.state == state
        assert job.completed_at is None

    def test_callback_from_superseded_attempt_refreshes_stale_instance(self):
        job = _job("push_submitted")
        DatasetJob.objects.filter(pk=job.pk).update(state="push_running", push_slurm_job_id="slurm-new")
        returned = submission.on_push_complete(job, False, job_id="slurm-old")
        assert returned is job
        assert job.state == "push_running"
        assert job.push_slurm_job_id == "slurm-new"

    def test_success_advances_to_completed(self):
        job = _job("push_running")
        submission.on_push_complete(job, True)
        job.refresh_from_db()
        assert job.state == "completed"
        assert job.completed_at is not None

    def test_failure_marks_failed_with_error(self):
        job = _job("push_running")
        submission.on_push_complete(job, False, error_message="s3 denied")
        job.refresh_from_db()
        assert job.state == "failed"
        assert job.error_message == "s3 denied"

    def test_success_clears_a_prior_error(self):
        job = _job("push_running")
        job.error_message = "transient earlier error"
        job.save()
        submission.on_push_complete(job, True)
        job.refresh_from_db()
        assert job.state == "completed"
        assert not job.error_message

    def test_stale_push_callback_ignored_outside_push_phase(self):
        job = _job("prep_running")
        submission.on_push_complete(job, True)
        job.refresh_from_db()
        assert job.state == "prep_running"  # untouched

    def test_syncs_dataset_status(self):
        job = _job("push_running")
        submission.on_push_complete(job, True)
        job.dataset.refresh_from_db()
        assert job.dataset.status == "pushed"

        failed = _job("push_running")
        submission.on_push_complete(failed, False, error_message="nope")
        failed.dataset.refresh_from_db()
        assert failed.dataset.status == "failed"


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["prep_submitted", "prep_running", "push_submitted", "push_running"])
@pytest.mark.parametrize("success", [True, False])
def test_dataset_save_failure_rolls_back_completion_and_allows_retry(state, success, monkeypatch):
    job = _job(state)
    job.dataset.status = "syncing"
    job.dataset.save()
    complete = submission.on_prep_complete if state in submission.PREP_ACTIVE else submission.on_push_complete
    original_save = Dataset.save

    def fail_after_save(dataset, *args, **kwargs):
        original_save(dataset, *args, **kwargs)
        raise RuntimeError("dataset save failed")

    with monkeypatch.context() as patch:
        patch.setattr(Dataset, "save", fail_after_save)
        with pytest.raises(RuntimeError, match="dataset save failed"):
            complete(job, success)

    job.refresh_from_db()
    job.dataset.refresh_from_db()
    assert job.state == state
    assert job.completed_at is None
    assert not job.error_message
    assert job.dataset.status == "syncing"

    complete(job, success)
    expected_state = "prep_completed" if state in submission.PREP_ACTIVE else "completed"
    assert job.state == (expected_state if success else "failed")
    job.dataset.refresh_from_db()
    assert job.dataset.status == job.dataset_status
