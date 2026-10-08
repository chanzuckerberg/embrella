"""JobStatusSyncer uses explicit user auth or its existing service-account default."""

from unittest.mock import Mock

import pytest
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
