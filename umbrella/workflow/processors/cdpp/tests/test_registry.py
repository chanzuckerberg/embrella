"""GET /cdpp/v1/pipelines/: one row per cdpp run, limited to the user's own runs unless staff."""

import pytest
from django.contrib.auth.models import User
from processes.models import JobLog, PipeExecution, ProcRun
from stores.models import Cluster, PathType

from .conftest import ROOT, SESSION

URL = "/cdpp/v1/pipelines/"
TREES = {
    "miss_alignment": {
        "plan": "czii-miss-alignment",
        "run": "run002",
        "dir": f"{ROOT}/miss_alignment/{SESSION}/run002",
        "fingerprint": "f1",
        "reused": True,
    },
    "copick": {
        "plan": "czii-copick",
        "run": "run003",
        "dir": f"{ROOT}/copick/{SESSION}/run003",
        "fingerprint": "f2",
        "reused": False,
    },
}


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="pw")


def _pipeline(cdpp_step, session, name, user, job_id, status="running", attempts=(), cdpp_dir=None):
    """A cdpp run whose execution was launched by `user` as `job_id`."""
    run = ProcRun.objects.create(name=name, proc_plan=cdpp_step.plan, msi_session=session)
    parameters = {"cluster_id": "czii", "_reserved_runs": {"trees": TREES, "pipeline_fingerprint": "p"}}
    if cdpp_dir:
        parameters["_cdpp"] = {"dir": cdpp_dir}
    if attempts:
        parameters["_attempts"] = [{"job_id": attempt} for attempt in attempts]
    PipeExecution.objects.create(
        proc_run=run, pipe_in_plan=cdpp_step, status=status, job_id=job_id, parameters=parameters
    )
    JobLog.objects.create(user=user, job_id=job_id, job_name=f"cdpp_{session.name}_{name}")
    return run


def _names(response):
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    return [pipeline["run_name"] for pipeline in data["pipelines"]]


@pytest.mark.django_db
def test_requires_login(client, cdpp_step):
    assert client.get(URL).status_code in (302, 401, 403)


@pytest.mark.django_db
def test_row_shape(logged_in_client, cdpp_step, test_msi_session, test_user):
    run = _pipeline(cdpp_step, test_msi_session, "run001", test_user, "900", cdpp_dir="/recorded/cdpp/run001")

    (pipeline,) = logged_in_client.get(URL).json()["pipelines"]

    # The czii cluster's proc_url: {http_base}krios1.processing/{proc_software}/{msi_session}/{proc_run}/
    base = f"{Cluster.objects.get(cluster_id='czii').http_base_url}krios1.processing"
    assert pipeline == {
        "session_name": SESSION,
        "run_name": "run001",
        "cluster_id": "czii",
        "status": "running",
        "created_at": run.created_at.isoformat(),
        "proc_run_id": run.id,
        "config_path": "/recorded/cdpp/run001/pipeline.yaml",
        "output_dir": "/recorded/cdpp/run001",
        "output_url": f"{base}/cdpp/{SESSION}/run001/",
        "config_url": f"{base}/cdpp/{SESSION}/run001/pipeline.yaml",
        "trees": {
            "miss_alignment": {
                "run": "run002",
                "dir": f"{ROOT}/miss_alignment/{SESSION}/run002",
                "reused": True,
                "url": f"{base}/miss_alignment/{SESSION}/run002/",
            },
            "copick": {
                "run": "run003",
                "dir": f"{ROOT}/copick/{SESSION}/run003",
                "reused": False,
                "url": f"{base}/copick/{SESSION}/run003/",
            },
        },
    }


@pytest.mark.django_db
def test_urls_are_null_without_a_proc_url(logged_in_client, cdpp_step, test_msi_session, test_user):
    PathType.objects.filter(data_kind__data_type="proc_url").delete()
    _pipeline(cdpp_step, test_msi_session, "run001", test_user, "900")

    (pipeline,) = logged_in_client.get(URL).json()["pipelines"]

    assert pipeline["output_url"] is None and pipeline["config_url"] is None
    assert {tree["url"] for tree in pipeline["trees"].values()} == {None}


@pytest.mark.django_db
def test_output_dir_falls_back_to_the_processing_root(logged_in_client, cdpp_step, test_msi_session, test_user):
    _pipeline(cdpp_step, test_msi_session, "run001", test_user, "900")

    (pipeline,) = logged_in_client.get(URL).json()["pipelines"]

    assert pipeline["output_dir"] == f"{ROOT}/cdpp/{SESSION}/run001"
    assert pipeline["config_path"] == f"{ROOT}/cdpp/{SESSION}/run001/pipeline.yaml"


@pytest.mark.django_db
def test_users_see_their_own_runs_and_staff_see_all(
    client, logged_in_client, cdpp_step, test_msi_session, test_user, other_user
):
    _pipeline(cdpp_step, test_msi_session, "run001", test_user, "901")
    _pipeline(cdpp_step, test_msi_session, "run002", other_user, "902")
    # Relaunched by someone else: the earlier attempt was the user's, so it is still theirs to see.
    _pipeline(cdpp_step, test_msi_session, "run003", other_user, "904", attempts=["903"])
    JobLog.objects.create(user=test_user, job_id="903", job_name="cdpp_24nov10_run003")

    assert sorted(_names(logged_in_client.get(URL))) == ["run001", "run003"]

    staff = User.objects.create_user(username="staffer", password="pw", is_staff=True)
    client.force_login(staff)
    assert sorted(_names(client.get(URL))) == ["run001", "run002", "run003"]


@pytest.mark.django_db
def test_filters(logged_in_client, cdpp_step, cdpp_plans, test_msi_session, test_session_plan, test_user):
    from tem.models import MsiSession

    other_session = MsiSession.objects.create(name="24nov11", session_plan=test_session_plan)
    _pipeline(cdpp_step, test_msi_session, "run001", test_user, "910", status="completed")
    _pipeline(cdpp_step, test_msi_session, "run002", test_user, "911", status="failed")
    _pipeline(cdpp_step, other_session, "run001", test_user, "912", status="running")

    assert sorted(_names(logged_in_client.get(URL, {"session_id": SESSION}))) == ["run001", "run002"]
    assert _names(logged_in_client.get(URL, {"status": "failed"})) == ["run002"]
    assert len(_names(logged_in_client.get(URL, {"status": "completed,running"}))) == 2
    assert len(_names(logged_in_client.get(URL, {"status": "all"}))) == 3
