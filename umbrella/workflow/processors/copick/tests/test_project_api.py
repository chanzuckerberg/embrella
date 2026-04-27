"""Tests for the /copick/v1/projects/ API endpoints."""

import pytest
from django.contrib.auth.models import User
from processes.models import Pipe, PipeExecution, PipeInPlan, ProcPlan, ProcRun, ProcSoftware
from stores.models import Cluster
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software


@pytest.fixture
def client(db, client):
    user = User.objects.create_user(username="tester", password="pw")
    client.force_login(user)
    return client


@pytest.fixture
def bruno_cluster(db):
    return Cluster.objects.update_or_create(
        cluster_id="bruno",
        defaults={
            "name": "Bruno",
            "http_base_url": "https://onsite.czbiohub.org/group.czii/",
            "ssh_hostname": "bruno.czbiohub.org",
        },
    )[0]


@pytest.fixture
def czii_cluster(db):
    return Cluster.objects.update_or_create(
        cluster_id="czii",
        defaults={
            "name": "CZII",
            "http_base_url": "https://czii-onsite.czbiohub.org/",
            "ssh_hostname": "czii.czbiohub.org",
        },
    )[0]


@pytest.fixture
def krios1_session(db):
    scope = Microscope.objects.create(name="Krios1", cs=2.7)
    camera = Camera.objects.create(
        name="K3", root_dir="/test/root", frame_format="eer", initial_frame_base_dir="/test/frames"
    )
    workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
    software = Software.objects.create(name="SerialEM")
    session_plan = SessionPlan.objects.create(scope=scope, camera=camera, imaging_workflow=workflow, software=software)
    return MsiSession.objects.create(name="26mar13b", session_plan=session_plan)


@pytest.fixture
def copick_plan(db):
    return ProcPlan.objects.create(name="czii-copick")


@pytest.fixture
def copick_pipe_in_plan(db, copick_plan):
    software = ProcSoftware.objects.create(name="copick", processor_class="copick")
    pipe = Pipe.objects.create(name="copick", software=software)
    return PipeInPlan.objects.create(name="copick", plan=copick_plan, pipe=pipe)


def _make_run(plan, session, name, cluster_id, status="completed", pipe_in_plan=None):
    run = ProcRun.objects.create(name=name, proc_plan=plan, msi_session=session)
    PipeExecution.objects.create(
        proc_run=run,
        pipe_in_plan=pipe_in_plan,
        status=status,
        parameters={"cluster_id": cluster_id},
    )
    return run


@pytest.mark.django_db
class TestListCopickProjects:
    def test_empty_when_no_copick_plan(self, client):
        response = client.get("/copick/v1/projects/")
        assert response.status_code == 200
        assert response.json() == {"success": True, "projects": []}

    def test_returns_completed_project(self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan):
        _make_run(copick_plan, krios1_session, "run002", "bruno", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["projects"]) == 1

        project = body["projects"][0]
        expected_root = "https://onsite.czbiohub.org/group.czii/krios1.processing/copick/26mar13b/run002/"
        assert project["session_name"] == "26mar13b"
        assert project["run_name"] == "run002"
        assert project["cluster_id"] == "bruno"
        assert project["scope"] == "krios1"
        assert project["root_url"] == expected_root
        assert project["config_url"] == expected_root + "config.json"
        assert project["data_url"] == expected_root
        assert project["status"] == "completed"

    def test_filters_out_non_completed_by_default(
        self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan
    ):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "failed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/")
        assert response.json()["projects"] == []

    def test_status_all_includes_failed(self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "failed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/?status=all")
        projects = response.json()["projects"]
        assert len(projects) == 1
        assert projects[0]["status"] == "failed"

    def test_cluster_filter(
        self,
        client,
        bruno_cluster,
        czii_cluster,
        krios1_session,
        copick_plan,
        copick_pipe_in_plan,
    ):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "completed", copick_pipe_in_plan)
        _make_run(copick_plan, krios1_session, "run002", "czii", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/?cluster=czii")
        projects = response.json()["projects"]
        assert len(projects) == 1
        assert projects[0]["run_name"] == "run002"
        assert projects[0]["cluster_id"] == "czii"
        assert projects[0]["root_url"].startswith("https://czii-onsite.czbiohub.org/")

    def test_cluster_filter_accepts_multiple_repeated(
        self,
        client,
        bruno_cluster,
        czii_cluster,
        krios1_session,
        copick_plan,
        copick_pipe_in_plan,
    ):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "completed", copick_pipe_in_plan)
        _make_run(copick_plan, krios1_session, "run002", "czii", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/?cluster=czii&cluster=bruno")
        projects = response.json()["projects"]
        assert {p["cluster_id"] for p in projects} == {"czii", "bruno"}
        assert len(projects) == 2

    def test_cluster_filter_accepts_comma_separated(
        self,
        client,
        bruno_cluster,
        czii_cluster,
        krios1_session,
        copick_plan,
        copick_pipe_in_plan,
    ):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "completed", copick_pipe_in_plan)
        _make_run(copick_plan, krios1_session, "run002", "czii", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/?cluster=czii,bruno")
        projects = response.json()["projects"]
        assert {p["cluster_id"] for p in projects} == {"czii", "bruno"}
        assert len(projects) == 2

    def test_no_cluster_filter_returns_all_clusters(
        self,
        client,
        bruno_cluster,
        czii_cluster,
        krios1_session,
        copick_plan,
        copick_pipe_in_plan,
    ):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "completed", copick_pipe_in_plan)
        _make_run(copick_plan, krios1_session, "run002", "czii", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/")
        projects = response.json()["projects"]
        assert {p["cluster_id"] for p in projects} == {"czii", "bruno"}
        assert len(projects) == 2

    def test_session_id_filter(self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan):
        _make_run(copick_plan, krios1_session, "run001", "bruno", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/?session_id=other_session")
        assert response.json()["projects"] == []

        response = client.get("/copick/v1/projects/?session_id=26mar13b")
        assert len(response.json()["projects"]) == 1

    def test_defaults_to_bruno_when_parameters_missing_cluster_id(
        self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan
    ):
        run = ProcRun.objects.create(name="run099", proc_plan=copick_plan, msi_session=krios1_session)
        PipeExecution.objects.create(
            proc_run=run,
            pipe_in_plan=copick_pipe_in_plan,
            status="completed",
            parameters={},
        )

        response = client.get("/copick/v1/projects/")
        projects = response.json()["projects"]
        assert len(projects) == 1
        assert projects[0]["cluster_id"] == "bruno"


@pytest.mark.django_db
class TestCopickProjectDetail:
    def test_returns_project(self, client, bruno_cluster, krios1_session, copick_plan, copick_pipe_in_plan):
        _make_run(copick_plan, krios1_session, "run002", "bruno", "completed", copick_pipe_in_plan)

        response = client.get("/copick/v1/projects/26mar13b/run002/")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["project"]["run_name"] == "run002"

    def test_404_for_unknown(self, client, bruno_cluster, copick_plan):
        response = client.get("/copick/v1/projects/does_not_exist/run001/")
        assert response.status_code == 404
        assert response.json()["success"] is False
