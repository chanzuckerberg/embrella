from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone
from workflow.log_fetcher import LIVE_LOG_COOLDOWN, logs_need_fetch


def execution(status, fetched=None, completed=None):
    return SimpleNamespace(status=status, logs_fetched_at=fetched, completed_at=completed)


def test_first_fetch_for_running_and_terminal():
    assert logs_need_fetch(execution("running"))
    assert logs_need_fetch(execution("completed"))
    assert logs_need_fetch(execution("failed"))
    assert not logs_need_fetch(execution("submitted"))


def test_terminal_fetches_once_after_end():
    ended = timezone.now() - timedelta(minutes=10)

    fetched_before_end = execution("completed", fetched=ended - timedelta(minutes=1), completed=ended)
    fetched_after_end = execution("completed", fetched=ended + timedelta(minutes=1), completed=ended)

    assert logs_need_fetch(fetched_before_end)
    assert not logs_need_fetch(fetched_after_end)


def test_running_respects_cooldown():
    # Clock read here, not at import: the suite may run longer than the cooldown.
    now = timezone.now()
    fresh = execution("running", fetched=now - LIVE_LOG_COOLDOWN / 2)
    stale = execution("running", fetched=now - LIVE_LOG_COOLDOWN * 2)

    assert not logs_need_fetch(fresh)
    assert logs_need_fetch(stale)
