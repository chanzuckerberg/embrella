"""Run-name allocation: DB ProcRuns and on-disk run directories both count as taken."""

from unittest.mock import Mock

import pytest
from processes.models import ProcPlan, ProcRun
from tem.models import MsiSession
from workflow import run_numbers
from workflow.run_numbers import list_run_dirs, next_run_name, next_run_name_from, reserve_run


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
def test_disk_directories_are_taken(test_proc_plan, test_msi_session):
    # A run dir created outside Embrella must not be reused.
    _runs(test_proc_plan, test_msi_session, "run001")

    assert next_run_name(test_msi_session, test_proc_plan, existing_dirs=["run005", "notes"]) == "run006"


@pytest.mark.django_db
def test_reserve_run_creates_distinct_runs(test_proc_plan, test_msi_session):
    first = reserve_run(test_msi_session, test_proc_plan, existing_dirs=["run002"])
    second = reserve_run(test_msi_session, test_proc_plan, existing_dirs=["run002"])

    assert (first.name, second.name) == ("run003", "run004")
    assert ProcRun.objects.filter(msi_session=test_msi_session, proc_plan=test_proc_plan).count() == 2


def test_list_run_dirs_over_ssh(monkeypatch):
    ssh = Mock()
    stdout = Mock()
    stdout.read.return_value = b"/proc/aretomo3/24nov10/run001\n/proc/aretomo3/24nov10/run002_old/\n"
    ssh.exec_command.return_value = (Mock(), stdout, Mock())
    connect = Mock(return_value=ssh)
    monkeypatch.setattr(run_numbers.clusterio, "get_cluster_ssh_connection", connect)

    assert list_run_dirs("/proc/aretomo3/", "24nov10", cluster_id="czii") == ["run001", "run002_old"]
    connect.assert_called_once_with(cluster_id="czii")
    assert ssh.exec_command.call_args.args[0] == "ls -1d /proc/aretomo3/24nov10/run* 2>/dev/null"
    ssh.close.assert_called_once_with()


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
