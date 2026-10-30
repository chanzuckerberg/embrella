"""Run-name allocation: the session's recorded ProcRuns are the names taken."""

import pytest
from processes.models import Pipe, PipeInPlan, ProcPlan, ProcRun, ProcSoftware
from tem.models import MsiSession
from workflow.run_numbers import list_run_dirs, next_run_name, next_run_name_from, plan_softwares, reserve_run


@pytest.mark.parametrize(
    "names, expected",
    [
        ([], "run001"),
        (["run001", "run002"], "run003"),
        (["run001", "run007"], "run008"),  # gaps are not refilled
        (["run002_old", "copick", "runabc", "run", "xrun009"], "run001"),  # not runNNN
        (["run998"], "run999"),
        (["run999"], "run1000"),
        (["run1000", "run999"], "run1001"),
        (["run5"], "run006"),
    ],
)
def test_next_run_name_from(names, expected):
    assert next_run_name_from(names) == expected


def _runs(proc_plan, msi_session, *names):
    for name in names:
        ProcRun.objects.create(name=name, proc_plan=proc_plan, msi_session=msi_session)


@pytest.mark.django_db
def test_counts_only_this_session_and_plan(test_proc_plan, test_msi_session, test_session_plan):
    _runs(test_proc_plan, test_msi_session, "run001", "run003")
    other_plan = ProcPlan.objects.create(name="other_plan")
    other_session = MsiSession.objects.create(name="24nov11", session_plan=test_session_plan)
    _runs(other_plan, test_msi_session, "run010")
    _runs(test_proc_plan, other_session, "run020")

    assert next_run_name(test_msi_session, test_proc_plan) == "run004"


@pytest.mark.django_db
def test_existing_dirs_are_taken(test_proc_plan, test_msi_session):
    _runs(test_proc_plan, test_msi_session, "run001")

    assert next_run_name(test_msi_session, test_proc_plan, existing_dirs=["run005", "notes"]) == "run006"


@pytest.mark.django_db
def test_reserve_run_creates_distinct_runs(test_proc_plan, test_msi_session):
    first = reserve_run(test_msi_session, test_proc_plan, existing_dirs=["run002"])
    second = reserve_run(test_msi_session, test_proc_plan, existing_dirs=["run002"])

    assert (first.name, second.name) == ("run003", "run004")
    assert ProcRun.objects.filter(msi_session=test_msi_session, proc_plan=test_proc_plan).count() == 2


def _plan(name, *softwares):
    plan = ProcPlan.objects.create(name=name)
    for step, software in enumerate(softwares, start=1):
        pipe = Pipe.objects.create(name=f"vol{step:03d}", software=software)
        PipeInPlan.objects.create(name=f"vol{step:03d}", plan=plan, step=step, pipe=pipe)
    return plan


@pytest.mark.django_db
def test_list_run_dirs_by_software(test_msi_session, test_session_plan):
    # Plans sharing a software share its directory; other software and sessions don't count.
    aretomo3 = ProcSoftware.objects.create(name="aretomo3-x", processor_class="aretomo3")
    denoise = ProcSoftware.objects.create(name="denoise-x", processor_class="denoiset")
    live, cdpp, other = _plan("live", aretomo3), _plan("cdpp-tree", aretomo3), _plan("denoise", denoise)
    other_session = MsiSession.objects.create(name="24nov11", session_plan=test_session_plan)
    _runs(live, test_msi_session, "run001")
    _runs(cdpp, test_msi_session, "run002")
    _runs(other, test_msi_session, "run009")
    _runs(live, other_session, "run020")

    assert sorted(list_run_dirs([aretomo3], test_msi_session)) == ["run001", "run002"]


@pytest.mark.django_db
def test_plan_runs_reports_next_run_name(logged_in_client, test_msi_session):
    plan, _ = ProcPlan.objects.get_or_create(name="czii-live")
    _runs(plan, test_msi_session, "run001", "run004")

    response = logged_in_client.get("/workflow/v1/execution/plan_runs/", {"plan_type": "aretomo3"})

    assert response.status_code == 200
    (session,) = response.json()["sessions"]
    assert session["name"] == "24nov10"
    assert sorted(session["run_numbers"]) == ["001", "004"]
    assert session["next_run_name"] == "run005"


@pytest.mark.django_db
def test_plan_runs_counts_sibling_plans_of_same_software(logged_in_client, test_msi_session):
    # A cdpp tree plan writing aretomo3 runs shares czii-live's directory.
    aretomo3 = ProcSoftware.objects.create(name="aretomo3-x", processor_class="aretomo3")
    live, sibling = _plan("czii-live", aretomo3), _plan("cdpp-tree", aretomo3)
    _runs(live, test_msi_session, "run001")
    _runs(sibling, test_msi_session, "run006")

    response = logged_in_client.get("/workflow/v1/execution/plan_runs/", {"plan_type": "aretomo3"})

    (session,) = response.json()["sessions"]
    assert session["run_numbers"] == ["001"]
    assert session["next_run_name"] == "run007"


@pytest.mark.django_db
def test_plan_runs_counts_every_chained_software(logged_in_client, test_msi_session):
    # A chained aretomo3 -> denoise plan needs its run name free under denoise's directory too.
    aretomo3 = ProcSoftware.objects.create(name="aretomo3-x", processor_class="aretomo3")
    denoise = ProcSoftware.objects.create(name="denoise-x", processor_class="denoiset")
    chained, standalone = _plan("cdpp-chain", aretomo3, denoise), _plan("czii-denoise", denoise)
    _runs(chained, test_msi_session, "run001")
    _runs(standalone, test_msi_session, "run004")

    assert sorted(list_run_dirs(plan_softwares(chained), test_msi_session)) == ["run001", "run004"]


@pytest.mark.django_db
def test_plan_runs_session_without_runs(logged_in_client, test_msi_session):
    ProcPlan.objects.get_or_create(name="czii-live")
    params = {"plan_type": "aretomo3", "session_name": test_msi_session.name}

    (session,) = logged_in_client.get("/workflow/v1/execution/plan_runs/", params).json()["sessions"]

    assert session == {"name": test_msi_session.name, "run_numbers": [], "next_run_name": "run001"}


@pytest.mark.django_db
def test_plan_runs_session_without_runs_counts_siblings(logged_in_client, test_msi_session):
    # First chained run in a session where standalone denoise already reached run004.
    aretomo3 = ProcSoftware.objects.create(name="aretomo3-x", processor_class="aretomo3")
    denoise = ProcSoftware.objects.create(name="denoise-x", processor_class="denoiset")
    _plan("czii-live", aretomo3, denoise)
    _runs(_plan("standalone-denoise", denoise), test_msi_session, "run004")
    params = {"plan_type": "aretomo3", "session_name": test_msi_session.name}

    (session,) = logged_in_client.get("/workflow/v1/execution/plan_runs/", params).json()["sessions"]

    assert session["run_numbers"] == []
    assert session["next_run_name"] == "run005"


@pytest.mark.django_db
def test_plan_runs_unknown_session_is_empty(logged_in_client):
    ProcPlan.objects.get_or_create(name="czii-live")
    params = {"plan_type": "aretomo3", "session_name": "no-such-session"}

    assert logged_in_client.get("/workflow/v1/execution/plan_runs/", params).json()["sessions"] == []
