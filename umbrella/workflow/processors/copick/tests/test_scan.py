"""Unit tests for the copick annotation scan."""

import json
from contextlib import contextmanager
from unittest import mock

import pytest
from django.contrib.auth.models import User
from processes.models import ProcPlan, ProcRun
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

from common import clusterio
from workflow.processors.copick import scan
from workflow.processors.copick import views as copick_views

COPICK_RUNS_URL = "/workflow/v1/processors/copick/runs/"
COPICK_DETAIL_URL = "/copick/v1/projects/{session}/{run}/"


@pytest.fixture
def client(db, client):
    """Django test client, logged in (the API auth middleware redirects anon requests)."""
    client.force_login(User.objects.create_user(username="tester", password="pw"))
    return client


@pytest.fixture
def copick_session(db):
    """An MsiSession with two copick ProcRuns under the czii-copick plan."""
    session_plan = SessionPlan.objects.create(
        scope=Microscope.objects.create(name="Krios1", cs=2.7),
        camera=Camera.objects.create(name="K3", root_dir="/r", frame_format="eer", initial_frame_base_dir="/f"),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="SerialEM"),
    )
    session = MsiSession.objects.create(name="26feb20b", session_plan=session_plan)
    plan = ProcPlan.objects.create(name="czii-copick")
    ProcRun.objects.create(name="run001", proc_plan=plan, msi_session=session)
    ProcRun.objects.create(name="run002", proc_plan=plan, msi_session=session)
    return session


class _FakeSftp:
    @contextmanager
    def file(self, *_args, **_kwargs):
        yield mock.Mock()  # the "with sftp.file(...) as f: f.write(...)" target

    def close(self):
        pass


class _FakeStream:
    def __init__(self, text=""):
        self._text = text

    def read(self):
        return self._text.encode("utf-8")


class _FakeSSH:
    def __init__(self, stdout="", stderr=""):
        self._stdout, self._stderr = stdout, stderr

    def open_sftp(self):
        return _FakeSftp()

    def exec_command(self, *_args, **_kwargs):
        return None, _FakeStream(self._stdout), _FakeStream(self._stderr)

    def close(self):
        pass


def _patch_ssh(ssh):
    return mock.patch.object(clusterio, "get_cluster_ssh_connection", return_value=ssh)


def test_scan_parses_picks_segs_meshes():
    payload = {
        "picks": [{"run_name": "TS_1", "object_name": "ribosome", "user_id": "u", "session_id": "0", "count": 12}],
        "segmentations": [{"run_name": "TS_1", "name": "membrane", "user_id": "u", "session_id": "0", "voxel_size": 10.0}],
        "meshes": [],
    }
    ssh = _FakeSSH(stdout="some conda noise\nCOPICK_SCAN_JSON:" + json.dumps(payload) + "\n")
    with _patch_ssh(ssh):
        result = scan.scan_copick_project("czii", "/hpc/.../config.json")
    assert result["scanned"] is True
    assert result["picks"] == payload["picks"]
    assert result["segmentations"] == payload["segmentations"]
    assert result["meshes"] == []


def test_scan_ssh_disabled_returns_empty():
    with mock.patch.object(
        clusterio, "get_cluster_ssh_connection", side_effect=clusterio.SSHDisabledError("off")
    ):
        result = scan.scan_copick_project("czii", "/hpc/.../config.json")
    assert result["scanned"] is False
    assert result["reason"] == "ssh_disabled"
    assert result["picks"] == [] and result["segmentations"] == [] and result["meshes"] == []


def test_scan_no_json_marker_returns_empty():
    ssh = _FakeSSH(stdout="ModuleNotFoundError: copick\n", stderr="boom")
    with _patch_ssh(ssh):
        result = scan.scan_copick_project("czii", "/hpc/.../config.json")
    assert result["scanned"] is False
    assert result["reason"] == "no_output"


def test_scan_copick_error_surfaced():
    ssh = _FakeSSH(stdout='COPICK_SCAN_JSON:{"error": "config not found"}\n')
    with _patch_ssh(ssh):
        result = scan.scan_copick_project("czii", "/hpc/.../config.json")
    assert result["scanned"] is False
    assert result["reason"] == "config not found"


@pytest.mark.django_db
class TestGetCopickRunsFromDB:
    """get_copick_runs lists copick ProcRuns from the DB (no filesystem/SSH/mount)."""

    def test_lists_copick_procruns(self, client, copick_session):
        r = client.get(COPICK_RUNS_URL, {"session_id": "26feb20b"})
        assert r.status_code == 200
        names = {x["name"] for x in r.json()["copick_runs"]}
        assert names == {"run001", "run002"}

    def test_unknown_session_returns_empty(self, client, db):
        r = client.get(COPICK_RUNS_URL, {"session_id": "does-not-exist"})
        assert r.status_code == 200
        assert r.json()["copick_runs"] == []

    def test_missing_session_id_is_400(self, client, db):
        r = client.get(COPICK_RUNS_URL)
        assert r.json()["success"] is False


@pytest.mark.django_db
class TestDetailScanWiring:
    """get_copick_project_detail attaches scanned annotations only when ?scan=true."""

    def test_scan_true_attaches_annotations(self, client, copick_session):
        annotations = {"picks": [{"run_name": "run001"}], "segmentations": [], "meshes": [], "scanned": True}
        with (
            mock.patch.object(copick_views, "_build_copick_project", return_value={"cluster_id": "czii"}),
            mock.patch.object(scan, "scan_copick_project", return_value=annotations) as scan_mock,
        ):
            r = client.get(COPICK_DETAIL_URL.format(session="26feb20b", run="run001"), {"scan": "true"})
        assert r.status_code == 200
        assert r.json()["project"]["annotations"] == annotations
        scan_mock.assert_called_once_with(
            "czii", "/hpc/projects/group.czii/krios1.processing/copick/26feb20b/run001/config.json"
        )

    def test_default_does_not_scan(self, client, copick_session):
        with (
            mock.patch.object(copick_views, "_build_copick_project", return_value={"cluster_id": "czii"}),
            mock.patch.object(scan, "scan_copick_project") as scan_mock,
        ):
            r = client.get(COPICK_DETAIL_URL.format(session="26feb20b", run="run001"))
        assert r.status_code == 200
        assert "annotations" not in r.json()["project"]
        scan_mock.assert_not_called()
