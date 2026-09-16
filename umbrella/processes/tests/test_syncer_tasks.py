from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_q.models import Schedule
from django_q.scheduler import scheduler
from tem.models import MsiSession

from processes.models import Pipe, PipeExecution, PipeInPlan, ProcPlan, ProcRun, ProcSoftware
from processes.tasks import syncer_tasks

FUNC = "processes.tasks.run_job_status_syncer"
ARGS = ("123", "bruno")
NAME = "job_status_123"
FAKE_TASK_ID = "0123456789abcdef0123456789abcdef"

SESSION = "26jun09a"
RUN = "run102"
JOB = "13765"
FAKE_SYNCER = f"{__name__}.FakeSyncer"


class FakeSyncer:
    # Stand-in for a ProcessSyncer subclass; counts sync passes.
    passes = 0

    def __init__(self, base_path, log_dir):
        self.job_id = None

    def setup(self, run_id, session_name, cluster_id=None):
        pass

    def sync_results(self):
        FakeSyncer.passes += 1


@pytest.fixture
def pipe_exec(session_plan):
    # The minimum chain run_syncer_iteration needs to find a job.
    session = MsiSession.objects.create(name=SESSION, session_plan=session_plan)
    software = ProcSoftware.objects.create(name="fixture-sync", processor_class="fixture-sync")
    plan = ProcPlan.objects.create(name="fixture-plan")
    pipe = Pipe.objects.create(name="fixture-pipe", software=software)
    pip = PipeInPlan.objects.create(name="fixture-pipe", plan=plan, pipe=pipe)
    run = ProcRun.objects.create(name=RUN, proc_plan=plan, msi_session=session)

    FakeSyncer.passes = 0
    return PipeExecution.objects.create(proc_run=run, pipe_in_plan=pip, job_id=JOB)


def run_iteration(job_active):
    with patch("processes.tasks.syncer_tasks.check_job_status", return_value=job_active):
        return syncer_tasks.run_syncer_iteration(FAKE_SYNCER, "/base", SESSION, RUN, JOB)


@pytest.mark.django_db
def test_iteration_syncs_then_reschedules_while_job_runs(pipe_exec):
    result = run_iteration(job_active=True)

    assert result["action"] == "synced_and_rescheduled"
    assert FakeSyncer.passes == 1
    assert Schedule.objects.filter(name=f"syncer_{SESSION}_{RUN}").exists()


@pytest.mark.django_db
def test_iteration_syncs_once_more_before_stopping(pipe_exec):
    # Files written between the last pass and job end must still be picked up.
    result = run_iteration(job_active=False)

    assert result["action"] == "stopped"
    assert FakeSyncer.passes == 1
    assert not Schedule.objects.filter(name=f"syncer_{SESSION}_{RUN}").exists()


def run_scheduler():
    # scheduler() closes "old" connections first; inside pytest-django's
    # test transaction that kills the MySQL connection. Sqlite masks it.
    with (
        patch("django_q.scheduler.close_old_django_connections"),
        patch("django_q.scheduler.async_task", return_value=FAKE_TASK_ID) as enqueue,
    ):
        scheduler()

    return enqueue


@pytest.mark.django_db
def test_run_later_fires_once_with_name_and_args():
    syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=-1), timeout=300)

    enqueue = run_scheduler()

    enqueue.assert_called_once()
    args, kwargs = enqueue.call_args
    assert args == (FUNC, *ARGS)
    assert kwargs["task_name"] == NAME
    assert kwargs["timeout"] == 300
    assert not Schedule.objects.filter(name=NAME).exists()


@pytest.mark.django_db
def test_run_later_waits_for_delay():
    syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=60))

    enqueue = run_scheduler()

    enqueue.assert_not_called()
    assert Schedule.objects.get(name=NAME).next_run > timezone.now()


@pytest.mark.django_db
def test_run_later_replaces_duplicate_name():
    for _ in range(2):
        syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=60))

    assert Schedule.objects.filter(name=NAME).count() == 1
