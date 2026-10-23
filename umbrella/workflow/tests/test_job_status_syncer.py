"""JobStatusSyncer: sacct credentials, and which PipeExecution rows a job's status reaches."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from processes.models import PipeExecution, ProcRun
from workflow import syncers


@pytest.mark.parametrize("user_auth", [None, {"username": "job-owner"}])
def test_sacct_connects_with_selected_credentials(monkeypatch, user_auth):
    service_auth = {"username": "service"}
    service = Mock(return_value=service_auth)
    ssh = Mock()
    stdout = Mock()
    stdout.read.return_value = b"123|Unknown|Unknown|00:00:00|RUNNING|0:0"
    ssh.exec_command.return_value = (Mock(), stdout, Mock())
    connect = Mock(return_value=ssh)
    monkeypatch.setattr(syncers.clusterio, "get_auth_service_user", service)
    monkeypatch.setattr(syncers.clusterio, "get_cluster_ssh_connection", connect)

    info = syncers.JobStatusSyncer(
        job_id="123", cluster_id="configured-cluster", auth=user_auth
    ).get_job_info_from_sacct()

    assert info["state"] == "RUNNING"
    connect.assert_called_once_with("configured-cluster", user_auth if user_auth is not None else service_auth)
    if user_auth is None:
        service.assert_called_once_with()
    else:
        service.assert_not_called()
    ssh.close.assert_called_once_with()


def _executions(test_pipe_in_plan, test_msi_session, job_ids):
    """One PipeExecution per job id, each on its own run."""
    return [
        PipeExecution.objects.create(
            proc_run=ProcRun.objects.create(
                name=f"run{index:03d}", proc_plan=test_pipe_in_plan.plan, msi_session=test_msi_session
            ),
            pipe_in_plan=test_pipe_in_plan,
            status="submitted",
            job_id=job_id,
        )
        for index, job_id in enumerate(job_ids, start=1)
    ]


@pytest.mark.django_db
def test_status_reaches_every_execution_sharing_the_job(test_pipe_in_plan, test_msi_session):
    # One SLURM job can back several run records; none may be left "submitted".
    executions = _executions(test_pipe_in_plan, test_msi_session, ["500", "500"])
    syncer = syncers.JobStatusSyncer(job_id="500", cluster_id="czii")

    syncer.setup()
    for execution in executions:
        execution.refresh_from_db()
        assert execution.syncer_active

    syncer.update_pipe_execution(
        {
            "state": "COMPLETED",
            "start_time": datetime(2026, 1, 1, 10, tzinfo=UTC),
            "end_time": datetime(2026, 1, 1, 11, tzinfo=UTC),
        }
    )
    for execution in executions:
        execution.refresh_from_db()
        assert execution.status == "completed"
        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert not execution.syncer_active


@pytest.mark.django_db
def test_hetjob_components_share_the_base_job_status(test_pipe_in_plan, test_msi_session):
    het_base, het_component, unrelated = _executions(test_pipe_in_plan, test_msi_session, ["600", "600+1", "6000"])

    syncer = syncers.JobStatusSyncer(job_id="600+0", cluster_id="czii")
    syncer.setup()
    syncer.update_pipe_execution(
        {"state": "RUNNING", "start_time": datetime(2026, 1, 1, 10, tzinfo=UTC), "end_time": None}
    )

    for execution in (het_base, het_component, unrelated):
        execution.refresh_from_db()
    assert het_base.status == het_component.status == "running"
    assert unrelated.status == "submitted"
    assert not unrelated.syncer_active
