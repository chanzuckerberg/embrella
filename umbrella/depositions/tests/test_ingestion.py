"""Upload-to-PR orchestration, including retries after an uncertain GitHub response."""

import base64
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
import yaml
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from depositions import tasks
from depositions.models import Dataset, DatasetJob, Deposition
from depositions.serializers import DatasetJobSerializer
from depositions.services import ingestion, submission

CONFIG = {
    "version": "1.1.0",
    "standardization_config": {
        "deposition_id": 101,
        "source_prefix": "CZII/101/202",
        "run_data_map_file": "run_to_data_map.tsv",
    },
    "datasets": [
        {
            "metadata": {
                "dataset_identifier": 202,
                "dates": {
                    "deposition_date": "2026-10-27",
                    "last_modified_date": "2026-10-27",
                    "release_date": "2026-10-27",
                },
            },
            "sources": [{"literal": {"value": ["202"]}}],
        }
    ],
    "depositions": [
        {
            "metadata": {"deposition_identifier": 101, "deposition_title": "Uploaded deposition"},
            "sources": [{"literal": {"value": [101]}}],
        }
    ],
    "runs": [{"sources": [{"source_glob": {"list_glob": "*.aln"}}]}],
    "voxel_spacings": [{"sources": [{"literal": {"value": [10.0]}}]}],
    "annotations": [
        {
            "metadata": {
                "annotation_ingest_id": "membrane-202",
                "annotation_object": {"id": "GO:0016020", "name": "membrane"},
            },
            "sources": [{"SemanticSegmentationMask": {"glob_string": "*_mask.mrc", "mask_label": 1}}],
        }
    ],
}


@pytest.fixture
def job(db, settings, tmp_path):
    settings.DEPOSITION_INGESTION_ENABLED = True
    settings.DEPOSITION_INGESTION_GITHUB_APP_ID = "123"
    settings.DEPOSITION_INGESTION_GITHUB_REPOSITORY = "test-org/ingestion-sandbox"
    settings.DEPOSITION_INGESTION_GITHUB_BASE_BRANCH = "staging"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_file = tmp_path / "app.pem"
    key_file.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    settings.DEPOSITION_INGESTION_GITHUB_KEY_PATH = str(key_file)
    owner = User.objects.create_user(username="owner")
    deposition = Deposition.objects.create(
        title="Deposition",
        description="Description",
        deposition_id=101,
        submitter_user=owner,
    )
    dataset = Dataset.objects.create(deposition=deposition, title="Dataset", dataset_id=202)
    return DatasetJob.objects.create(dataset=dataset, state="completed", cluster_id="czii", push_slurm_job_id="42")


class GitHubServer:
    def __init__(self, repository, base_branch):
        self.repository = repository
        self.base_branch = base_branch
        self.branch = False
        self.files = {}
        self.pr = None
        self.creates = 0
        self.lose_response = False
        self.token_requests = []

    def request(self, method, url, **kwargs):
        if url == "https://api.github.com/app/installations/321/access_tokens":
            self.token_requests.append(kwargs["json"])
            response = Mock(status_code=201)
            response.json.return_value = {"token": "installation-token"}
            return response
        path = url.split(f"/{self.repository}/")[1]
        data, code = {}, 200
        if path == "installation":
            data = {"id": 321}
        elif path == "pulls" and method == "GET":
            assert kwargs["params"]["head"].startswith(self.repository.split("/")[0] + ":")
            assert kwargs["params"]["base"] == self.base_branch
            data = [self.pr] if self.pr else []
        elif path == "pulls":
            assert kwargs["json"]["base"] == self.base_branch
            self.creates += 1
            self.pr = {"html_url": "https://github.com/chanzuckerberg/cryoet-data-portal-backend/pull/999"}
            data = self.pr
            if self.lose_response:
                self.lose_response = False
                raise requests.Timeout("Response lost after creating the PR")
        elif path == f"git/ref/heads/{self.base_branch}":
            data = {"object": {"sha": "base-sha"}}
        elif path.startswith("git/ref/heads/"):
            code = 200 if self.branch else 404
        elif path == "git/refs":
            self.branch = True
        elif method == "PUT":
            self.files[path] = {**kwargs["json"], "sha": "file-sha"}
        elif path.startswith("contents/"):
            if kwargs["params"]["ref"] != self.base_branch and path in self.files:
                data = self.files[path]
            else:
                code = 404
        else:
            raise AssertionError((method, path))
        response = Mock(status_code=code)
        response.json.return_value = data
        return response


@pytest.fixture
def github(monkeypatch, settings, job):
    server = GitHubServer(
        settings.DEPOSITION_INGESTION_GITHUB_REPOSITORY, settings.DEPOSITION_INGESTION_GITHUB_BASE_BRANCH
    )
    session = Mock()
    session.request.side_effect = server.request
    monkeypatch.setattr(ingestion.requests, "Session", lambda: session)
    server.session = session
    return server


@pytest.fixture
def uploaded(monkeypatch, settings):
    settings.DEPOSITION_AWS_PROFILE = "upload-profile"
    result = SimpleNamespace(content="# Already validated before upload\n" + yaml.safe_dump(CONFIG), ssh=Mock())

    def execute(command, **kwargs):
        stdout, stderr = Mock(), Mock()
        stdout.read.return_value = result.content.encode() if "s3 cp" in command else b"{}"
        stdout.channel.recv_exit_status.return_value = 0
        stderr.read.return_value = b""
        return Mock(), stdout, stderr

    result.ssh.exec_command.side_effect = execute
    result.connect = Mock(return_value=result.ssh)
    monkeypatch.setattr(ingestion.clusterio, "get_cluster_ssh_connection", result.connect)
    monkeypatch.setattr(ingestion.clusterio, "get_auth_service_user", lambda: {"username": "service"})
    monkeypatch.setattr(ingestion, "resolve_sync_destination", lambda **kw: "s3://bucket/CZII")
    return result


def test_successful_upload_queues_once_and_stale_callbacks_do_not(job, monkeypatch, django_capture_on_commit_callbacks):
    enqueue = Mock()
    monkeypatch.setattr(ingestion, "async_task", enqueue)
    job.state = "push_running"
    job.save()
    with django_capture_on_commit_callbacks(execute=True):
        submission.on_push_complete(job, True, job_id="old")
        assert not enqueue.called
        submission.on_push_complete(job, True, job_id="42")
        submission.on_push_complete(job, True, job_id="42")
    enqueue.assert_called_once()
    job.refresh_from_db()
    assert job.state == "completed" and job.ingestion_state == "not_started" and job.ingestion_attempt


def test_ingestion_queue_error_does_not_undo_upload_completion(job, monkeypatch, django_capture_on_commit_callbacks):
    monkeypatch.setattr(ingestion, "queue_ingestion_pr", Mock(side_effect=RuntimeError("Queue unavailable")))
    job.state = "push_running"
    job.save()
    with django_capture_on_commit_callbacks(execute=True):
        submission.on_push_complete(job, True, job_id="42")
    job.refresh_from_db()
    assert job.state == "completed" and job.dataset.status == "pushed"
    assert job.ingestion_state == "failed" and job.ingestion_branch and job.ingestion_error


def test_expired_queued_attempt_can_be_requeued(job, monkeypatch, django_capture_on_commit_callbacks):
    enqueue = Mock()
    monkeypatch.setattr(ingestion, "async_task", enqueue)
    job.ingestion_attempt = "lost-task"
    job.save()
    with django_capture_on_commit_callbacks(execute=True):
        ingestion.queue_ingestion_pr(job)
    enqueue.assert_not_called()
    assert DatasetJobSerializer(job).data["ingestion_retryable"] is False
    DatasetJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=16))
    job.refresh_from_db()
    assert DatasetJobSerializer(job).data["ingestion_retryable"] is True
    with django_capture_on_commit_callbacks(execute=True):
        queued = ingestion.queue_ingestion_pr(job)
    enqueue.assert_called_once()
    assert queued.ingestion_attempt != "lost-task"


def test_worker_preserves_uploaded_yaml_and_recovers_a_created_pr(
    job, github, uploaded, monkeypatch, django_capture_on_commit_callbacks
):
    monkeypatch.setattr(ingestion, "async_task", Mock())
    github.lose_response = True
    with django_capture_on_commit_callbacks(execute=True):
        queued = ingestion.queue_ingestion_pr(job)
    first = queued.ingestion_attempt
    tasks.create_ingestion_pr(job.pk, first)
    job.refresh_from_db()
    assert job.state == "completed" and job.ingestion_state == "failed"
    assert github.creates == 1
    submission.on_push_complete(job, True, job_id="42")
    job.refresh_from_db()
    assert job.ingestion_state == "failed"  # A duplicate completion does not enqueue another PR attempt.
    with django_capture_on_commit_callbacks(execute=True):
        queued = ingestion.queue_ingestion_pr(job)
    second = queued.ingestion_attempt
    tasks.create_ingestion_pr(job.pk, first)  # A late delivery cannot claim the new attempt.
    tasks.create_ingestion_pr(job.pk, second)
    tasks.create_ingestion_pr(job.pk, second)
    job.refresh_from_db()
    assert job.ingestion_state == "pr_opened" and job.ingestion_pr_url == github.pr["html_url"]
    assert job.ingestion_branch == "deposition-101-dataset-202"
    assert job.last_validated_hash == hashlib.sha256(uploaded.content.encode()).hexdigest()
    assert github.creates == 1
    assert set(github.files) == {"contents/ingestion_tools/dataset_configs/202.yaml"}
    committed = github.files["contents/ingestion_tools/dataset_configs/202.yaml"]["content"]
    assert base64.b64decode(committed) == uploaded.content.encode()


def test_incomplete_uploaded_yaml_never_writes_to_github(job, github, uploaded):
    uploaded.content = "datasets: []\n"
    job.ingestion_attempt = "attempt"
    job.save()
    tasks.create_ingestion_pr(job.pk, "attempt")
    job.refresh_from_db()
    assert job.ingestion_state == "failed" and "missing sections" in job.ingestion_error
    assert job.state == "completed" and not github.branch and not github.files and not github.creates


def test_missing_app_key_leaves_upload_completed_and_ingestion_retryable(job, uploaded, settings):
    settings.DEPOSITION_INGESTION_GITHUB_KEY_PATH = "/dev/null"
    job.ingestion_attempt = "attempt"
    job.save()
    tasks.create_ingestion_pr(job.pk, "attempt")
    job.refresh_from_db()
    assert job.state == "completed"
    assert job.ingestion_state == "failed" and "not provisioned" in job.ingestion_error
    uploaded.connect.assert_not_called()


def test_defining_dataset_cannot_open_pr_without_uploaded_deposition_metadata(job, github, uploaded):
    deposition = job.dataset.deposition
    deposition.metadata_config_dataset = job.dataset
    deposition.save(update_fields=["metadata_config_dataset"])
    config = yaml.safe_load(uploaded.content)
    config["depositions"][0].pop("metadata")
    uploaded.content = yaml.safe_dump(config)
    job.ingestion_attempt = "attempt"
    job.save()
    tasks.create_ingestion_pr(job.pk, "attempt")
    job.refresh_from_db()
    assert job.state == "completed" and job.ingestion_state == "failed"
    assert "supports deposition_metadata" in job.ingestion_error
    assert not github.branch and not github.files and not github.creates


def test_reads_s3_config_and_datamap_using_upload_credentials(job, uploaded):
    content, uri = ingestion._read_uploaded_config(job)
    assert uri == "s3://bucket/CZII/101/202"
    assert content == uploaded.content
    assert "--profile upload-profile" in uploaded.ssh.exec_command.call_args_list[0].args[0]
    assert "CZII/101/202/run_to_data_map.tsv" in uploaded.ssh.exec_command.call_args_list[1].args[0]
    uploaded.connect.assert_called_once_with("czii", auth={"username": "service"})
    uploaded.ssh.close.assert_called_once()
    uploaded.content = uploaded.content.replace("CZII/101/202", "wrong/prefix")
    with pytest.raises(ValueError, match="source_prefix"):
        ingestion._read_uploaded_config(job)


def test_retry_endpoint_is_owner_only_and_hides_private_errors(job, monkeypatch, django_capture_on_commit_callbacks):
    enqueue = Mock()
    monkeypatch.setattr(ingestion, "async_task", enqueue)
    job.ingestion_state = "failed"
    job.ingestion_error = "private cluster path"
    job.save()
    client = APIClient()
    other = User.objects.create_user(username="other")
    client.force_authenticate(other)
    url = f"/depositions/v1/datasets/{job.dataset.pk}/ingestion/retry/"
    assert client.post(url).status_code == 403
    result = client.get(f"/depositions/v1/datasets/{job.dataset.pk}/job-status/")
    assert result.json()["ingestion_error"] == ""
    client.force_authenticate(job.dataset.deposition.submitter_user)
    with django_capture_on_commit_callbacks(execute=True):
        assert client.post(url).status_code == 202
    enqueue.assert_called_once()


def test_app_auth_uses_signed_jwt_and_repository_scoped_token(job, github, settings):
    client = ingestion.GitHubIngestionPR()
    auth = github.session.headers.update.call_args_list[0].args[0]["Authorization"].split()[1]
    header, claims, signature = auth.split(".")
    private = serialization.load_pem_private_key(
        Path(settings.DEPOSITION_INGESTION_GITHUB_KEY_PATH).read_bytes(), password=None
    )
    private.public_key().verify(
        base64.urlsafe_b64decode(signature + "=="), f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    assert json.loads(base64.urlsafe_b64decode(claims + "=="))["iss"] == "123"
    assert github.token_requests == [
        {"repositories": ["ingestion-sandbox"], "permissions": {"contents": "write", "pull_requests": "write"}}
    ]
    assert github.session.headers.update.call_args.args[0]["Authorization"] == "Bearer installation-token"
    client.session.close()
