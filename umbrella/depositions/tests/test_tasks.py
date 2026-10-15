"""Tests for the deposition completion syncer task."""

import pytest

from depositions import tasks
from depositions.models import Dataset, DatasetJob, Deposition


class FakeSyncer:
    info = {"state": "COMPLETED", "exit_code": "0:0"}
    terminal = True
    raises = False
    last_auth = None

    def __init__(self, job_id, cluster_id, auth=None):
        self.job_id = job_id
        self.cluster_id = cluster_id
        self.auth = auth
        type(self).last_auth = auth

    def get_job_info_from_sacct(self):
        if type(self).raises:
            raise RuntimeError("ssh down")
        return type(self).info

    def is_job_terminal(self, info):
        return type(self).terminal


def _job(state, **fields):
    dep = Deposition.objects.create(title="Dep", deposition_id=1)
    ds = Dataset.objects.create(deposition=dep, title="DS", dataset_id=2)
    return DatasetJob.objects.create(dataset=ds, state=state, **fields)


@pytest.fixture(autouse=True)
def patched(monkeypatch):
    import workflow.syncers

    monkeypatch.setattr(tasks.clusterio, "get_auth_service_user", lambda: {"username": "service-user"})

    FakeSyncer.info = {"state": "COMPLETED", "exit_code": "0:0"}
    FakeSyncer.terminal = True
    FakeSyncer.raises = False
    FakeSyncer.last_auth = None
    monkeypatch.setattr(workflow.syncers, "JobStatusSyncer", FakeSyncer)
    import depositions.services.launch as launch_mod

    monkeypatch.setattr(launch_mod, "cancel_deposition_job", lambda **kw: None)
    # Don't open SSH in unit tests; a failure captures this stub tail onto the row.
    monkeypatch.setattr(tasks.logs, "capture_failure_tail", lambda *a: "captured tail")
    reschedules = []
    monkeypatch.setattr(tasks, "_reschedule", lambda *a: reschedules.append(a))
    return reschedules


@pytest.mark.django_db
class TestRunDepositionJobSyncer:
    def test_terminal_success_completes_prep(self, patched):
        job = _job("prep_running", prep_slurm_job_id="123")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        job.refresh_from_db()
        assert result["status"] == "terminal" and result["success"]
        assert job.state == "prep_completed"
        assert job.prep_completed_at is not None
        assert patched == []  # terminal: no reschedule

    def test_poll_uses_service_account_auth(self, patched):
        # sacct is queried as the service account.
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        assert FakeSyncer.last_auth == {"username": "service-user"}

    def test_terminal_failure_fails_push(self, patched):
        FakeSyncer.info = {"state": "FAILED", "exit_code": "1:0"}
        job = _job("push_running", push_slurm_job_id="99")
        tasks.run_deposition_job_syncer(job.id, "push", "bruno", "99")
        job.refresh_from_db()
        assert job.state == "failed"
        assert "FAILED" in job.error_message
        assert job.log_excerpt == "captured tail"

    def test_terminal_failure_captures_tail_with_poll_auth(self, patched, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            tasks.logs,
            "capture_failure_tail",
            lambda cluster_id, auth, phase, job_id: captured.update(args=(cluster_id, auth, phase, job_id)) or "tail",
        )
        FakeSyncer.info = {"state": "FAILED", "exit_code": "1:0"}
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        assert captured["args"] == ("bruno", {"username": "service-user"}, "prep", "123")

    def test_terminal_success_does_not_capture_a_tail(self, patched, monkeypatch):
        monkeypatch.setattr(tasks.logs, "capture_failure_tail", lambda *a: pytest.fail("no tail read on success"))
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        job.refresh_from_db()
        assert job.state == "prep_completed"

    def test_completed_with_nonzero_exit_is_a_failure(self, patched):
        FakeSyncer.info = {"state": "COMPLETED", "exit_code": "1:0"}
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        job.refresh_from_db()
        assert job.state == "failed"
        assert "exit 1:0" in job.error_message

    def test_running_reschedules_without_touching_state(self, patched):
        FakeSyncer.info = {"state": "RUNNING"}
        FakeSyncer.terminal = False
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        job.refresh_from_db()
        assert job.state == "prep_running"
        assert len(patched) == 1

    def test_running_promotes_submitted_to_running(self, patched):
        FakeSyncer.info = {"state": "RUNNING"}
        FakeSyncer.terminal = False
        job = _job("prep_submitted", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        job.refresh_from_db()
        assert job.state == "prep_running"
        assert len(patched) == 1

    def test_not_in_sacct_yet_reschedules(self, patched):
        FakeSyncer.info = None
        job = _job("prep_running", prep_slurm_job_id="123")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        assert result["status"] == "waiting"
        assert len(patched) == 1

    def test_waits_for_id_before_querying_sacct(self, patched):
        job = _job("prep_running", prep_slurm_job_id="")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123")
        assert result["status"] == "waiting_id"
        assert len(patched) == 1

    def test_superseded_attempt_stops_without_touching_state(self, patched):
        job = _job("prep_running", prep_slurm_job_id="new")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "old")
        job.refresh_from_db()
        assert result["status"] == "superseded"
        assert job.state == "prep_running"
        assert patched == []

    def test_missing_job_stops(self, patched):
        result = tasks.run_deposition_job_syncer(999999, "prep", "bruno", "x")
        assert result["status"] == "gone"
        assert patched == []

    def test_gives_up_after_max_waiting_in_sacct(self, patched):
        FakeSyncer.info = None  # never appears in sacct
        job = _job("prep_submitted", prep_slurm_job_id="123")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123", attempts=tasks.MAX_WAIT_ATTEMPTS)
        job.refresh_from_db()
        assert result["status"] == "gave_up"
        assert job.state == "failed"
        assert "never started" in job.error_message
        assert patched == []  # no further reschedule once we give up

    def test_running_resets_the_wait_counter(self, patched):
        FakeSyncer.info = {"state": "RUNNING"}
        FakeSyncer.terminal = False
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123", attempts=5)
        assert patched[0][4] == 0  # attempts arg reset to 0 while the job is live

    def test_blank_id_at_limit_stops_without_failing(self, patched):
        # An old poller must never fail a row whose id was reset by a newer claim.
        job = _job("prep_submitted", prep_slurm_job_id="")
        result = tasks.run_deposition_job_syncer(
            job.id, "prep", "bruno", "old-attempt", attempts=tasks.MAX_WAIT_ATTEMPTS
        )
        job.refresh_from_db()
        assert result == {"status": "gave_up", "reason": "no_id"}
        assert job.state == "prep_submitted"  # left for the new attempt's poller, not failed
        assert patched == []

    def test_error_give_up_cancels_then_fails(self, patched, monkeypatch):
        import depositions.services.launch as launch_mod

        cancelled = {}
        monkeypatch.setattr(
            launch_mod,
            "cancel_deposition_job",
            lambda *, cluster_id, job_id, auth: cancelled.update(id=job_id, cluster=cluster_id, auth=auth),
        )
        FakeSyncer.raises = True
        job = _job("prep_running", prep_slurm_job_id="123")
        result = tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123", attempts=tasks.MAX_WAIT_ATTEMPTS)
        job.refresh_from_db()
        assert result == {"status": "gave_up", "reason": "error"}
        assert cancelled == {
            "id": "123",
            "cluster": "bruno",
            "auth": {"username": "service-user"},
        }  # cancelled before failing, as the service account
        assert job.state == "failed"

    def test_push_gives_up_and_fails_with_stored_id(self, patched):
        # A push give-up has a stored id, so on_push_complete (require_attempt=True) still matches it.
        FakeSyncer.info = None
        job = _job("push_running", push_slurm_job_id="99")
        result = tasks.run_deposition_job_syncer(job.id, "push", "bruno", "99", attempts=tasks.MAX_WAIT_ATTEMPTS)
        job.refresh_from_db()
        assert result["status"] == "gave_up"
        assert job.state == "failed"

    def test_never_started_give_up_skips_log_capture(self, patched, monkeypatch):
        calls = []
        monkeypatch.setattr(tasks.logs, "capture_failure_tail", lambda *a: calls.append(a))
        FakeSyncer.info = None  # never appears in sacct
        job = _job("prep_submitted", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123", attempts=tasks.MAX_WAIT_ATTEMPTS)
        job.refresh_from_db()
        assert job.state == "failed"
        assert calls == []  # no SSH read for a job that never started

    def test_error_give_up_leaves_row_if_cancel_fails(self, patched, monkeypatch):
        import depositions.services.launch as launch_mod

        def cancel_boom(*, cluster_id, job_id, auth):
            raise OSError("scancel failed")

        monkeypatch.setattr(launch_mod, "cancel_deposition_job", cancel_boom)
        FakeSyncer.raises = True
        job = _job("prep_running", prep_slurm_job_id="123")
        tasks.run_deposition_job_syncer(job.id, "prep", "bruno", "123", attempts=tasks.MAX_WAIT_ATTEMPTS)
        job.refresh_from_db()
        # Can't confirm the job stopped, so don't make it retryable into a double-run.
        assert job.state == "prep_running"


@pytest.mark.django_db
def test_give_up_cancels_with_service_account(patched, monkeypatch):
    import depositions.services.launch as launch_mod

    job = _job("prep_running", prep_slurm_job_id="123")
    cancelled = []
    monkeypatch.setattr(launch_mod, "cancel_deposition_job", lambda **kwargs: cancelled.append(kwargs))
    assert tasks._give_up(job, "prep", "bruno", "123", "test")
    assert cancelled == [{"cluster_id": "bruno", "job_id": "123", "auth": {"username": "service-user"}}]


def _raise_no_creds():
    raise RuntimeError("service credentials unavailable")


@pytest.mark.django_db
def test_give_up_snapshots_log_tail_and_reason(patched):
    job = _job("prep_running", prep_slurm_job_id="123")
    assert tasks._give_up(job, "prep", "bruno", "123", "boom reason")
    job.refresh_from_db()
    assert job.state == "failed"
    assert job.error_message == "boom reason"
    assert job.log_excerpt == "captured tail"


@pytest.mark.django_db
def test_give_up_without_credentials_leaves_job_for_operator(patched, monkeypatch):
    import depositions.services.launch as launch_mod

    job = _job("prep_running", prep_slurm_job_id="123")
    cancelled = []
    monkeypatch.setattr(tasks.clusterio, "get_auth_service_user", _raise_no_creds)
    monkeypatch.setattr(launch_mod, "cancel_deposition_job", lambda **kwargs: cancelled.append(kwargs))
    assert not tasks._give_up(job, "prep", "bruno", "123", "test")
    job.refresh_from_db()
    assert job.state == "prep_running"
    assert cancelled == []


def test_job_auth_returns_none_when_service_creds_unavailable(monkeypatch):
    # The poller/cancel path treats unresolved creds as "no auth" (then reschedules/leaves the row).
    monkeypatch.setattr(tasks.clusterio, "get_auth_service_user", _raise_no_creds)
    assert tasks._job_auth() is None
