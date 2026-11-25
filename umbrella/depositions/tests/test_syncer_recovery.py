"""The reconciler restarts deposition job syncers whose poll chain has died."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from depositions import tasks
from depositions.apps import _ensure_syncer_reconciler_schedule
from depositions.models import Dataset, DatasetJob, Deposition

STALE = timedelta(minutes=20)  # past SYNCER_STALE_AFTER


def _job(state, *, syncer_active, polled_at, prep_id="slurm-1"):
    dep = Deposition.objects.create(title="D")
    ds = Dataset.objects.create(deposition=dep)
    return DatasetJob.objects.create(
        dataset=ds,
        state=state,
        cluster_id="cluster-a",
        prep_slurm_job_id=prep_id,
        syncer_active=syncer_active,
        syncer_polled_at=polled_at,
    )


@pytest.mark.django_db
def test_reconciler_restarts_only_jobs_with_a_dead_poll_chain():
    now = timezone.now()
    crashed = _job("prep_running", syncer_active=True, polled_at=now - STALE)
    never_started = _job("prep_submitted", syncer_active=False, polled_at=None)
    healthy = _job("prep_running", syncer_active=True, polled_at=now)
    terminal = _job("completed", syncer_active=False, polled_at=None)

    with mock.patch("depositions.tasks.start_deposition_job_syncer") as start:
        result = tasks.reconcile_deposition_syncers()

    restarted = {call.args[0] for call in start.call_args_list}
    assert restarted == {crashed.id, never_started.id}
    assert healthy.id not in restarted and terminal.id not in restarted
    assert set(result["restarted"]) == {crashed.id, never_started.id}


@pytest.mark.django_db
def test_reconciler_skips_rows_with_no_slurm_id():
    # No cluster job to monitor (mid-launch, or a launch that never recorded an id) — don't restart a poller
    # that can't progress.
    job = _job("prep_submitted", syncer_active=False, polled_at=None, prep_id="")
    with mock.patch("depositions.tasks.start_deposition_job_syncer") as start:
        result = tasks.reconcile_deposition_syncers()
    assert job.id not in {call.args[0] for call in start.call_args_list}
    assert result["restarted"] == []


@pytest.mark.django_db
def test_reconciler_restarts_with_phase_and_ids_from_the_job():
    job = _job("push_running", syncer_active=True, polled_at=timezone.now() - STALE, prep_id="")
    DatasetJob.objects.filter(pk=job.pk).update(push_slurm_job_id="slurm-push")
    with mock.patch("depositions.tasks.start_deposition_job_syncer") as start:
        tasks.reconcile_deposition_syncers()
    start.assert_called_once_with(job.id, "push", "cluster-a", "slurm-push")


@pytest.mark.django_db
def test_start_marks_the_syncer_active_with_a_heartbeat():
    job = _job("prep_submitted", syncer_active=False, polled_at=None)
    with mock.patch("depositions.tasks.async_task"):
        tasks.start_deposition_job_syncer(job.id, "prep", "cluster-a", "slurm-1")
    job.refresh_from_db()
    assert job.syncer_active is True
    assert job.syncer_polled_at is not None


@pytest.mark.django_db
def test_run_sets_heartbeat_then_clears_active_on_giveup():
    # The poll iteration stamps the heartbeat; giving up clears syncer_active. (no_id path needs no cluster.)
    job = _job("prep_submitted", syncer_active=False, polled_at=None, prep_id="")
    out = tasks.run_deposition_job_syncer(job.id, "prep", "cluster-a", "", attempts=tasks.MAX_WAIT_ATTEMPTS)
    assert out == {"status": "gave_up", "reason": "no_id"}
    job.refresh_from_db()
    assert job.state == "prep_submitted"  # no_id give-up leaves the row untouched, never fails it
    assert job.syncer_polled_at is not None
    assert job.syncer_active is False


@pytest.mark.django_db
def test_superseded_attempt_leaves_the_flags_alone():
    # A retry replaced the attempt; the stale poller exits without touching the live attempt's flags.
    polled = timezone.now() - STALE
    job = _job("prep_running", syncer_active=True, polled_at=polled)
    out = tasks.run_deposition_job_syncer(job.id, "prep", "cluster-a", "old-attempt")
    assert out == {"status": "superseded"}
    job.refresh_from_db()
    assert job.syncer_active is True
    assert job.syncer_polled_at == polled


@pytest.mark.django_db
def test_schedule_registration_is_idempotent():
    from django_q.models import Schedule

    Schedule.objects.filter(name="deposition_syncer_reconciler").delete()
    _ensure_syncer_reconciler_schedule(sender=None)
    _ensure_syncer_reconciler_schedule(sender=None)
    assert Schedule.objects.filter(name="deposition_syncer_reconciler").count() == 1
