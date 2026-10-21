"""Only an owner can cancel their current upload, through the service account."""

from unittest.mock import Mock

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from depositions.models import Dataset, DatasetJob, Deposition
from depositions.services import submit


@pytest.fixture
def upload(db, monkeypatch):
    owner = User.objects.create_user(username="upload-owner")
    deposition = Deposition.objects.create(title="Dep", submitter_user=owner)
    dataset = Dataset.objects.create(deposition=deposition, title="DS")
    job = DatasetJob.objects.create(dataset=dataset, state="push_running", cluster_id="bruno", push_slurm_job_id="123")
    cancel = Mock()
    monkeypatch.setattr(submit, "cancel_deposition_job", cancel)
    monkeypatch.setattr(submit, "_service_auth", lambda: {"username": "service-account"})
    client = APIClient()
    client.force_authenticate(owner)
    return client, job, cancel, f"/depositions/v1/datasets/{dataset.pk}/cancel-upload/"


def test_cancels_current_upload_and_waits_for_scheduler_confirmation(upload):
    client, job, cancel, url = upload
    response = client.post(url, {"job_id": "123"}, format="json")
    assert response.status_code == 202
    cancel.assert_called_once_with(cluster_id="bruno", job_id="123", auth={"username": "service-account"})
    job.refresh_from_db()
    assert job.state == "push_running"  # scancel acceptance does not mean the job has stopped yet.


@pytest.mark.parametrize("state,job_id", [("push_running", "old"), ("completed", "123")])
def test_rejects_stale_or_finished_upload_attempts(upload, state, job_id):
    client, job, cancel, url = upload
    job.state = state
    job.save(update_fields=["state"])
    response = client.post(url, {"job_id": job_id}, format="json")
    assert response.status_code == 400
    cancel.assert_not_called()


def test_other_users_cannot_cancel_service_account_jobs(upload):
    client, _, cancel, url = upload
    other = User.objects.create_user(username="other-owner")
    client.force_authenticate(other)
    assert client.post(url, {"job_id": "123"}, format="json").status_code == 403
    cancel.assert_not_called()


def test_cluster_failure_does_not_unlock_upload_or_expose_diagnostics(upload):
    client, job, cancel, url = upload
    cancel.side_effect = OSError("private cluster diagnostics")
    response = client.post(url, {"job_id": "123"}, format="json")
    assert response.status_code == 502
    assert response.json() == {"detail": "Couldn't cancel the upload. Please try again."}
    job.refresh_from_db()
    assert job.state == "push_running"
