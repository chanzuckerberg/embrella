"""Unit tests for the deposition job-log reader."""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.core.cache import cache

from depositions.services import logs

SVC_AUTH = {"username": "service-user", "pkey": "k"}


@pytest.fixture(autouse=True)
def _clear_log_cache():
    """The live-read cooldown uses the process cache; isolate it between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _service_auth():
    """Deposition log reads run as the service account."""
    with mock.patch.object(logs.clusterio, "get_auth_service_user", return_value=SVC_AUTH):
        yield


def _job(**kw):
    defaults = {
        "pk": 1,
        "state": "prep_running",
        "prep_slurm_job_id": "111",
        "push_slurm_job_id": "",
        "cluster_id": "bruno",
        "log_excerpt": "stored tail",
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _dataset(job):
    return SimpleNamespace(pk=1, job=job)


def test_no_job_returns_empty():
    assert logs.fetch_job_logs(SimpleNamespace(pk=1, job=None)) == {"logs": "", "state": None, "source": "none"}


def test_no_slurm_id_falls_back_to_stored():
    out = logs.fetch_job_logs(_dataset(_job(prep_slurm_job_id="")))
    assert out == {"logs": "stored tail", "state": "prep_running", "phase": "prep", "source": "stored"}


def test_missing_cluster_id_falls_back_to_stored():
    out = logs.fetch_job_logs(_dataset(_job(cluster_id="")))
    assert out["source"] == "stored"


def test_non_owner_gets_stored_without_a_live_read():
    # A non-owner must not trigger a service-account SSH read.
    with mock.patch.object(logs, "_read_slurm_tail", side_effect=AssertionError("should not read")) as read:
        out = logs.fetch_job_logs(_dataset(_job()), live=False)
    assert out == {"logs": "stored tail", "state": "prep_running", "phase": "prep", "source": "stored"}
    read.assert_not_called()


def test_service_auth_failure_falls_back_to_stored_without_erroring():
    # A missing service key must not 500 the logs endpoint.
    with mock.patch.object(logs.clusterio, "get_auth_service_user", side_effect=RuntimeError("ssh disabled")):
        out = logs.fetch_job_logs(_dataset(_job()))
    assert out["source"] == "stored"
    assert out["logs"] == "stored tail"


def test_read_failure_reports_unavailable_with_the_stored_fallback():
    with mock.patch.object(logs, "_read_slurm_tail", side_effect=OSError("no such file")):
        out = logs.fetch_job_logs(_dataset(_job()))
    assert out["source"] == "unavailable"  # distinguishable from an empty "stored" log
    assert out["logs"] == "stored tail"


def test_live_read_returns_tail():
    with mock.patch.object(logs, "_read_slurm_tail", return_value="live output") as read:
        out = logs.fetch_job_logs(_dataset(_job()))
    read.assert_called_once_with("bruno", SVC_AUTH, "prep", "111")
    assert out == {"logs": "live output", "state": "prep_running", "phase": "prep", "job_id": "111", "source": "live"}


def test_live_read_is_cached_within_cooldown():
    with mock.patch.object(logs, "_read_slurm_tail", return_value="once") as read:
        first = logs.fetch_job_logs(_dataset(_job()))
        second = logs.fetch_job_logs(_dataset(_job()))
    assert first == second
    read.assert_called_once()  # second request served from cache — no new SSH


def test_failed_read_is_cached_to_throttle_a_down_cluster():
    with mock.patch.object(logs, "_read_slurm_tail", side_effect=OSError("cluster down")) as read:
        first = logs.fetch_job_logs(_dataset(_job()))
        second = logs.fetch_job_logs(_dataset(_job()))
    assert first["source"] == "unavailable"
    assert second["source"] == "unavailable"
    read.assert_called_once()  # second poll served the cached failure — no new SSH attempt


def test_cache_hit_reflects_current_state_not_the_cooldown_snapshot():
    job = _job(state="prep_running")
    with mock.patch.object(logs, "_read_slurm_tail", return_value="log") as read:
        first = logs.fetch_job_logs(_dataset(job))
        job.state = "prep_completed"  # job finished during the cooldown
        second = logs.fetch_job_logs(_dataset(job))
    assert first["state"] == "prep_running"
    assert second["state"] == "prep_completed"  # fresh state, not the frozen cached snapshot
    read.assert_called_once()  # still served from cache


def test_read_slurm_tail_delegates_to_clusterio():
    with (
        mock.patch.object(logs.clusterio, "read_remote_file_tail", return_value="tail") as read,
        mock.patch.object(logs, "get_processor") as get_processor,
    ):
        get_processor.return_value.get_script_directory.return_value = "/scripts"
        out = logs._read_slurm_tail("bruno", {"username": "a"}, "prep", "111")

    read.assert_called_once_with(
        "bruno", "/scripts/slurm-111.out", max_bytes=logs.MAX_LOG_BYTES, auth={"username": "a"}
    )
    assert out == "tail"


def test_push_phase_selects_push_job():
    job = _job(state="push_running", push_slurm_job_id="222")
    with mock.patch.object(logs, "_read_slurm_tail", return_value="push log") as read:
        logs.fetch_job_logs(_dataset(job))
    assert read.call_args.args[2:] == ("push", "222")


def test_failed_push_selects_push_log_over_prep():
    job = _job(state="failed", prep_slurm_job_id="111", push_slurm_job_id="222")
    assert logs._active_attempt(job) == ("push", "222")


def test_failed_prep_selects_prep_log():
    job = _job(state="failed", prep_slurm_job_id="111", push_slurm_job_id="")
    assert logs._active_attempt(job) == ("prep", "111")
