"""Tests for the copick scan - endpoints read the cached scan.json.

The scan itself now runs as a SLURM job (CopickScanProcessor) that writes an aggregated
scan.json next to config.json; the endpoints read it over caddy via _read_scan_json.
"""

import json
from unittest import mock

import pytest
from django.contrib.auth.models import User
from processes.models import ProcPlan, ProcRun
from rest_framework.test import APIClient
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

from workflow.processors.copick import views as copick_views

COPICK_RUNS_URL = "/workflow/v1/processors/copick/runs/"
COPICK_DETAIL_URL = "/copick/v1/projects/{session}/{run}/"
ANNOTATED_COUNT_URL = "/workflow/v1/processors/copick/annotated-count/"


@pytest.fixture
def client(db, client):
    """Django test client."""
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


@pytest.mark.django_db
class TestGetCopickRuns:
    """get_copick_runs merges DB ProcRuns with cluster-listed configs."""

    def _no_cluster(self):
        return mock.patch.object(copick_views, "_list_cluster_copick_runs", return_value=set())

    def test_lists_copick_procruns(self, client, copick_session):
        with self._no_cluster():
            r = client.get(COPICK_RUNS_URL, {"session_id": "26feb20b"})
        assert r.status_code == 200
        names = {x["name"] for x in r.json()["copick_runs"]}
        assert names == {"run001", "run002"}

    def test_merges_cluster_configs_not_in_db(self, client, copick_session):
        # run004 exists on the cluster but has no ProcRun — it must still appear.
        with mock.patch.object(copick_views, "_list_cluster_copick_runs", return_value={"run004", "run001"}):
            r = client.get(COPICK_RUNS_URL, {"session_id": "26feb20b"})
        names = {x["name"] for x in r.json()["copick_runs"]}
        assert names == {"run001", "run002", "run004"}  # DB ∪ cluster, deduped

    def test_unknown_session_returns_empty(self, client, db):
        with self._no_cluster():
            r = client.get(COPICK_RUNS_URL, {"session_id": "does-not-exist"})
        assert r.status_code == 200
        assert r.json()["copick_runs"] == []

    def test_missing_session_id_is_400(self, client, db):
        r = client.get(COPICK_RUNS_URL)
        assert r.json()["success"] is False


@pytest.mark.django_db
class TestDetailScanWiring:
    """get_copick_project_detail attaches the cached scan.json only when ?scan=true."""

    def test_scan_true_attaches_annotations(self, client, copick_session):
        ann = {
            "scanned": True,
            "picks": [{"copick_ref": "ribosome:u/0", "run_count": 3, "total_count": 12}],
            "segmentations": [],
            "meshes": [],
            "annotated_runs": ["run001"],
        }
        with (
            mock.patch.object(
                copick_views, "_build_copick_project", return_value={"root_url": "http://caddy/26feb20b/run001/"}
            ),
            mock.patch.object(copick_views, "_read_scan_json", return_value=ann) as read_mock,
        ):
            r = client.get(COPICK_DETAIL_URL.format(session="26feb20b", run="run001"), {"scan": "true"})
        assert r.status_code == 200
        assert r.json()["project"]["annotations"] == ann
        read_mock.assert_called_once_with("http://caddy/26feb20b/run001/")

    def test_cluster_only_run_without_procrun_still_serves_scan(self, client, copick_session):
        """A config selectable from the cluster but with no ProcRun (run999) must not 404 — it
        resolves the path from (session, run) and serves scan.json (else it's permanently unreadable)."""
        ann = {"scanned": True, "picks": [], "segmentations": [], "meshes": [], "annotated_runs": []}
        with (
            mock.patch.object(copick_views, "_copick_root_url", return_value="http://caddy/26feb20b/run999/"),
            mock.patch.object(copick_views, "_read_scan_json", return_value=ann) as read_mock,
        ):
            r = client.get(COPICK_DETAIL_URL.format(session="26feb20b", run="run999"), {"scan": "true"})
        assert r.status_code == 200
        assert r.json()["project"]["annotations"] == ann
        read_mock.assert_called_once_with("http://caddy/26feb20b/run999/")

    def test_unknown_session_still_404s(self, client, db):
        r = client.get(COPICK_DETAIL_URL.format(session="does-not-exist", run="run001"), {"scan": "true"})
        assert r.status_code == 404

    def test_default_does_not_scan(self, client, copick_session):
        with (
            mock.patch.object(copick_views, "_build_copick_project", return_value={"root_url": "http://caddy/x/"}),
            mock.patch.object(copick_views, "_read_scan_json") as read_mock,
        ):
            r = client.get(COPICK_DETAIL_URL.format(session="26feb20b", run="run001"))
        assert r.status_code == 200
        assert "annotations" not in r.json()["project"]
        read_mock.assert_not_called()


class TestReadScanJson:
    """_read_scan_json normalizes every return to carry the annotation list keys."""

    def test_cluster_error_scan_still_has_list_keys(self):
        """A cluster-side failure writes {scanned, error} with no lists"""
        with mock.patch.object(
            copick_views, "fetch_remote_text", return_value='{"scanned": false, "error": "no copick"}'
        ):
            result = copick_views._read_scan_json("http://caddy/x/")
        assert result == {**copick_views._empty_scan(), "error": "no copick"}


@pytest.mark.django_db
class TestAnnotatedCountEndpoint:
    """annotated-count unions annotated_runs from each selected config's cached scan.json."""

    URL = ANNOTATED_COUNT_URL

    def _fake_url(self):
        return mock.patch.object(copick_views, "_copick_root_url", side_effect=lambda _s, run: f"http://caddy/{run}/")

    def test_aggregates_across_runs(self, client, copick_session):
        def fake_read(root_url):
            if "run002" in root_url:
                return {"scanned": True, "annotated_runs": ["TS_1"]}
            return {"scanned": True, "annotated_runs": ["TS_2"]}

        with self._fake_url(), mock.patch.object(copick_views, "_read_scan_json", side_effect=fake_read):
            r = client.get(self.URL, {"session_id": "26feb20b", "runs": "run002,run003"})
        body = r.json()
        assert r.status_code == 200
        assert body["annotated_count"] == 2
        assert body["annotated_runs"] == ["TS_1", "TS_2"]
        assert body["scanned"] is True

    def test_pending_scan_marks_not_scanned(self, client, copick_session):
        with (
            self._fake_url(),
            mock.patch.object(copick_views, "_read_scan_json", return_value={"scanned": False, "annotated_runs": []}),
        ):
            r = client.get(self.URL, {"session_id": "26feb20b", "runs": "run001"})
        body = r.json()
        assert body["scanned"] is False
        assert body["annotated_count"] == 0

    def test_resolve_failure_degrades_not_500(self, client, copick_session):
        """A per-run path/cluster lookup failure."""
        with mock.patch.object(copick_views, "_copick_root_url", side_effect=RuntimeError("no cluster row")):
            r = client.get(self.URL, {"session_id": "26feb20b", "runs": "run001"})
        assert r.status_code == 200
        body = r.json()
        assert body["scanned"] is False
        assert body["annotated_count"] == 0

    def test_no_runs_returns_zero_without_reading(self, client, copick_session):
        with mock.patch.object(copick_views, "_read_scan_json") as read_mock:
            r = client.get(self.URL, {"session_id": "26feb20b"})
        assert r.json()["annotated_count"] == 0
        read_mock.assert_not_called()

    def test_missing_session_id_is_error(self, client, db):
        r = client.get(self.URL, {"runs": "run002"})
        assert r.json()["success"] is False


@pytest.mark.django_db
class TestCopickScanWiring:
    def test_scan_plan_and_pipe_exist(self):
        from processes.models import PipeInPlan, ProcPlan, ProcSoftware

        assert ProcSoftware.objects.filter(processor_class="copick-scan").exists()
        plan = ProcPlan.objects.get(name="copick-scan")
        pip = PipeInPlan.objects.get(plan=plan)
        assert pip.pipe.software.processor_class == "copick-scan"

    def test_light_slurm_directives_from_schema(self):
        """The scan's light resources (cpu/4/8G/30min) must reach the #SBATCH lines — they come from
        the schema's x-slurm-directive props, NOT get_default_slurm_options (which isn't wired to jobs)."""
        from workflow.processors import get_processor

        p = get_processor("copick-scan")
        assert p.task_name == "copick_scan"
        pairs = {(d["directive"], str(d["value"])) for d in p.generate_slurm_directives({})}
        assert ("--partition", "cpu") in pairs
        assert ("--cpus-per-task", "4") in pairs
        assert ("--mem-per-cpu", "8G") in pairs
        assert ("--time", "00:30:00") in pairs

    def test_render_resolves_paths_and_emits_light_sbatch(self, db):
        """render_script de-hardcodes paths AND writes the light #SBATCH lines into the script."""
        from stores.paths import resolve_dir

        from workflow.processors import get_processor as real_get_processor

        proc = real_get_processor("copick-scan")
        run_context = mock.Mock(run_number="run003", cluster_id=None)
        run_context.msi_session.name = "25oct20a"

        # Feed the *real* directives (from the schema) through, so the render proves they land as #SBATCH.
        ctx = {"slurm_directives": proc.generate_slurm_directives({})}
        with (
            mock.patch.object(type(proc), "get_template_context", return_value=ctx),
            mock.patch("workflow.processors.copick.scan_processor.get_processor") as gp,
        ):
            gp.return_value.get_processing_base_path.return_value = "/hpc/krios1.processing/copick"
            script = proc.render_script({}, run_context)

        assert "/hpc/krios1.processing/copick/25oct20a/run003/config.json" in script
        assert "/hpc/krios1.processing/copick/25oct20a/run003/scan.json" in script
        assert resolve_dir("dataportal_env", cluster=None) in script
        assert "#SBATCH --partition=cpu" in script
        assert "#SBATCH --time=00:30:00" in script


SCAN_URL = "/copick/v1/projects/{session}/{run}/scan/"


@pytest.fixture
def api(db):
    """DRF client, authenticated (force_authenticate skips CSRF/session for the POST)."""
    c = APIClient()
    c.force_authenticate(User.objects.create_user(username="svc-tester", password="pw"))
    return c


@pytest.mark.django_db
class TestTriggerCopickScan:
    """POST .../scan/ submits the copick-scan job (service SSH) and returns immediately."""

    def test_submits_scan_job_and_returns_202(self, api, copick_session):
        with (
            mock.patch.object(copick_views.clusterio, "get_auth_service_user", return_value={"username": "svc"}),
            mock.patch.object(copick_views, "_invalidate_scan_json") as invalidate,
            mock.patch.object(copick_views, "cluster_id_for_run", return_value="czii"),
            mock.patch("workflow.execution.PipelineExecutor") as Executor,
        ):
            Executor.return_value.execute_pipe.return_value = {"job_id": "9001"}
            r = api.post(SCAN_URL.format(session="26feb20b", run="run001"))

        assert r.status_code == 202
        body = r.json()
        assert body["success"] is True
        assert body["job_id"] == "9001"
        # invalidate the old scan.json BEFORE submitting
        invalidate.assert_called_once_with("czii", "26feb20b", "run001")
        # submitted the copick-scan pipe with SERVICE auth (not per-user), no client params
        _, kwargs = Executor.return_value.execute_pipe.call_args
        assert kwargs["pipe_in_plan"].pipe.software.processor_class == "copick-scan"
        assert kwargs["auth"] == {"username": "svc"}
        assert kwargs["parameters"] == {}
        assert kwargs["cluster_id"] == "czii"
        # ProcRun reused under the copick-scan plan, named as the copick project run
        assert ProcRun.objects.filter(name="run001", proc_plan__name="copick-scan").exists()

    def test_rescan_clears_prior_execution_row(self, api, copick_session):
        """Re-scan reuses the same run+pipe; PipeExecution(run,pipe) is unique_together, so the prior
        row must be cleared before submit or the second scan 1062s (the live bug this fixes)."""
        from processes.models import PipeExecution, PipeInPlan, ProcPlan, ProcRun

        plan = ProcPlan.objects.get(name="copick-scan")
        pip = PipeInPlan.objects.get(plan=plan)
        session = MsiSession.objects.get(name="26feb20b")
        proc_run = ProcRun.objects.create(name="run001", proc_plan=plan, msi_session=session)
        stale = PipeExecution.objects.create(proc_run=proc_run, pipe_in_plan=pip, status="submitted", job_id="old")

        with (
            mock.patch.object(copick_views.clusterio, "get_auth_service_user", return_value={"username": "svc"}),
            mock.patch.object(copick_views, "_invalidate_scan_json"),
            mock.patch.object(copick_views, "cluster_id_for_run", return_value="czii"),
            mock.patch("workflow.execution.PipelineExecutor") as Executor,
        ):
            Executor.return_value.execute_pipe.return_value = {"job_id": "new"}
            r = api.post(SCAN_URL.format(session="26feb20b", run="run001"))

        assert r.status_code == 202
        assert not PipeExecution.objects.filter(id=stale.id).exists()  # prior row cleared → no 1062

    def test_tolerates_duplicate_procruns(self, api, copick_session):
        """Duplicate ProcRuns for the same (session, run, plan) must not crash the trigger with
        MultipleObjectsReturned — ProcRun has no unique constraint, so races can leave more than one."""
        from processes.models import ProcPlan, ProcRun

        plan = ProcPlan.objects.get(name="copick-scan")
        session = MsiSession.objects.get(name="26feb20b")
        ProcRun.objects.create(name="run001", proc_plan=plan, msi_session=session)
        ProcRun.objects.create(name="run001", proc_plan=plan, msi_session=session)  # duplicate

        with (
            mock.patch.object(copick_views.clusterio, "get_auth_service_user", return_value={"username": "svc"}),
            mock.patch.object(copick_views, "_invalidate_scan_json"),
            mock.patch.object(copick_views, "cluster_id_for_run", return_value="czii"),
            mock.patch("workflow.execution.PipelineExecutor") as Executor,
        ):
            Executor.return_value.execute_pipe.return_value = {"job_id": "9001"}
            r = api.post(SCAN_URL.format(session="26feb20b", run="run001"))
        assert r.status_code == 202  # used the earliest ProcRun, no MultipleObjectsReturned

    def test_requires_login(self, copick_session):
        r = APIClient().post(SCAN_URL.format(session="26feb20b", run="run001"))
        # DRF IsAuthenticated → 401/403; a global LoginRequiredMiddleware may 302 to login instead.
        assert r.status_code in (302, 401, 403)

    def test_unknown_session_is_404(self, api, db):
        r = api.post(SCAN_URL.format(session="does-not-exist", run="run001"))
        assert r.status_code == 404
        assert r.json()["success"] is False

    def test_ssh_disabled_degrades_to_503(self, api, copick_session):
        with (
            mock.patch.object(copick_views, "_invalidate_scan_json"),
            mock.patch.object(copick_views, "_mark_scan_failed") as mark_failed,
            mock.patch.object(copick_views, "cluster_id_for_run", return_value="czii"),
            mock.patch.object(
                copick_views.clusterio,
                "get_auth_service_user",
                side_effect=copick_views.clusterio.SSHDisabledError("off"),
            ),
        ):
            r = api.post(SCAN_URL.format(session="26feb20b", run="run001"))
        assert r.status_code == 503
        assert r.json()["success"] is False
        mark_failed.assert_called_once()  # pending marker cleared so polling doesn't hang

    def test_submit_failure_clears_pending_and_502s(self, api, copick_session):
        """A failed submit must clear the pending marker it just wrote, else polling spins forever."""
        with (
            mock.patch.object(copick_views, "_invalidate_scan_json"),
            mock.patch.object(copick_views, "_mark_scan_failed") as mark_failed,
            mock.patch.object(copick_views, "cluster_id_for_run", return_value="czii"),
            mock.patch.object(copick_views.clusterio, "get_auth_service_user", return_value={"username": "svc"}),
            mock.patch("workflow.execution.PipelineExecutor") as Executor,
        ):
            Executor.return_value.execute_pipe.side_effect = RuntimeError("sbatch blew up")
            r = api.post(SCAN_URL.format(session="26feb20b", run="run001"))
        assert r.status_code == 502
        mark_failed.assert_called_once()


@pytest.mark.django_db
class TestInvalidateScanJson:
    """_invalidate_scan_json writes a pending marker so polling can tell a new job from the last."""

    def test_writes_pending_marker_next_to_config(self):
        with (
            mock.patch("workflow.processors.get_processor") as get_processor,
            mock.patch.object(copick_views.clusterio, "write_remote_file") as writer,
        ):
            get_processor.return_value.get_processing_base_path.return_value = "/copick/base/"
            copick_views._invalidate_scan_json("czii", "26feb20b", "run001")

        writer.assert_called_once()
        args, _ = writer.call_args
        assert args[0] == "czii"
        assert args[1] == "/copick/base/26feb20b/run001/scan.json"
        payload = json.loads(args[2])
        # pending:true distinguishes "job running" from a missing file ("never scanned")
        assert payload["scanned"] is False
        assert payload["pending"] is True

    def test_write_failure_is_non_fatal(self):
        with (
            mock.patch("workflow.processors.get_processor") as get_processor,
            mock.patch.object(copick_views.clusterio, "write_remote_file", side_effect=FileNotFoundError("no dir")),
        ):
            get_processor.return_value.get_processing_base_path.return_value = "/copick/base/"
            copick_views._invalidate_scan_json("czii", "26feb20b", "run001")  # must not raise
