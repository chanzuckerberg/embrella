"""Unit tests for the deposition job-log reader."""

from types import SimpleNamespace
from unittest import mock

import pytest
from accounts.cluster_usernames import MissingClusterCredentialsError
from django.core.cache import cache

from depositions.services import logs


@pytest.fixture(autouse=True)
def _clear_log_cache():
    """The live-read cooldown uses the process cache; isolate it between tests."""
    cache.clear()
    yield
    cache.clear()


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
    assert logs.fetch_job_logs(SimpleNamespace(pk=1, job=None), user=object()) == {
        "logs": "",
        "state": None,
        "source": "none",
    }


def test_no_slurm_id_falls_back_to_stored():
    out = logs.fetch_job_logs(_dataset(_job(prep_slurm_job_id="")), user=object())
    assert out == {"logs": "stored tail", "state": "prep_running", "phase": "prep", "source": "stored"}


def test_missing_cluster_id_falls_back_to_stored():
    out = logs.fetch_job_logs(_dataset(_job(cluster_id="")), user=object())
    assert out["source"] == "stored"


def test_missing_ssh_setup_falls_back_to_stored():
    with mock.patch.object(logs.clusterio, "get_auth_for_user", side_effect=MissingClusterCredentialsError(1, "bruno")):
        out = logs.fetch_job_logs(_dataset(_job()), user=object())
    assert out == {"logs": "stored tail", "state": "prep_running", "phase": "prep", "source": "stored"}


def test_read_failure_falls_back_to_stored():
    with (
        mock.patch.object(logs.clusterio, "get_auth_for_user", return_value=({"username": "alice"}, None)),
        mock.patch.object(logs, "_read_slurm_tail", side_effect=OSError("no such file")),
    ):
        out = logs.fetch_job_logs(_dataset(_job()), user=object())
    assert out["source"] == "stored"
    assert out["logs"] == "stored tail"


def test_live_read_returns_tail():
    with (
        mock.patch.object(logs.clusterio, "get_auth_for_user", return_value=({"username": "alice"}, None)),
        mock.patch.object(logs, "_read_slurm_tail", return_value="live output") as read,
    ):
        out = logs.fetch_job_logs(_dataset(_job()), user=object())
    read.assert_called_once_with("bruno", {"username": "alice"}, "prep", "111")
    assert out == {"logs": "live output", "state": "prep_running", "phase": "prep", "job_id": "111", "source": "live"}


def test_live_read_is_cached_within_cooldown():
    with (
        mock.patch.object(logs.clusterio, "get_auth_for_user", return_value=({"username": "a"}, None)),
        mock.patch.object(logs, "_read_slurm_tail", return_value="once") as read,
    ):
        first = logs.fetch_job_logs(_dataset(_job()), user=object())
        second = logs.fetch_job_logs(_dataset(_job()), user=object())
    assert first == second
    read.assert_called_once()  # second request served from cache — no new SSH


def test_read_slurm_tail_caps_read_even_if_file_grows():
    # stat() sees 10 bytes, but the file grows before read() — the read must still be capped.
    handle = mock.MagicMock()
    handle.read.return_value = b"x" * logs.MAX_LOG_BYTES
    handle.__enter__.return_value = handle
    sftp = mock.MagicMock()
    sftp.stat.return_value = SimpleNamespace(st_size=10)
    sftp.file.return_value = handle
    ssh = mock.MagicMock()
    ssh.open_sftp.return_value = sftp

    with (
        mock.patch.object(logs.clusterio, "get_cluster_ssh_connection", return_value=ssh),
        mock.patch.object(logs, "get_processor") as get_processor,
    ):
        get_processor.return_value.get_script_directory.return_value = "/scripts"
        out = logs._read_slurm_tail("bruno", {"username": "a"}, "prep", "111")

    handle.read.assert_called_once_with(logs.MAX_LOG_BYTES)
    assert len(out) == logs.MAX_LOG_BYTES


def test_push_phase_selects_push_job():
    job = _job(state="push_running", push_slurm_job_id="222")
    with (
        mock.patch.object(logs.clusterio, "get_auth_for_user", return_value=({"username": "a"}, None)),
        mock.patch.object(logs, "_read_slurm_tail", return_value="push log") as read,
    ):
        logs.fetch_job_logs(_dataset(job), user=object())
    assert read.call_args.args[2:] == ("push", "222")


def test_failed_push_selects_push_log_over_prep():
    job = _job(state="failed", prep_slurm_job_id="111", push_slurm_job_id="222")
    phase, job_id = logs._active_attempt(job)
    assert (phase, job_id) == ("push", "222")


def test_failed_prep_selects_prep_log():
    job = _job(state="failed", prep_slurm_job_id="111", push_slurm_job_id="")
    phase, job_id = logs._active_attempt(job)
    assert (phase, job_id) == ("prep", "111")
