from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_q.models import Schedule
from django_q.scheduler import scheduler

from processes.tasks import syncer_tasks

FUNC = "processes.tasks.run_job_status_syncer"
ARGS = ("123", "bruno")
NAME = "job_status_123"
FAKE_TASK_ID = "0123456789abcdef0123456789abcdef"


@pytest.mark.django_db
def test_run_later_fires_once_with_name_and_args():
    syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=-1), timeout=300)

    with patch("django_q.scheduler.async_task", return_value=FAKE_TASK_ID) as enqueue:
        scheduler()

    enqueue.assert_called_once()
    args, kwargs = enqueue.call_args
    assert args == (FUNC, *ARGS)
    assert kwargs["task_name"] == NAME
    assert kwargs["timeout"] == 300
    assert not Schedule.objects.filter(name=NAME).exists()


@pytest.mark.django_db
def test_run_later_waits_for_delay():
    syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=60))

    with patch("django_q.scheduler.async_task", return_value=FAKE_TASK_ID) as enqueue:
        scheduler()

    enqueue.assert_not_called()
    assert Schedule.objects.get(name=NAME).next_run > timezone.now()


@pytest.mark.django_db
def test_run_later_replaces_duplicate_name():
    for _ in range(2):
        syncer_tasks._run_later(FUNC, ARGS, name=NAME, delay=timedelta(seconds=60))

    assert Schedule.objects.filter(name=NAME).count() == 1
