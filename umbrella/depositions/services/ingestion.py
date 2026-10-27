"""Create a Data Portal ingestion PR from the config of a completed upload."""

import base64
import hashlib
import json
import logging
import shlex
import time
import uuid
from datetime import timedelta
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

import requests
import yaml
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_q.tasks import async_task

from common import clusterio
from depositions.models import DatasetJob
from depositions.services.dataprep_config import resolve_sync_destination
from depositions.services.exceptions import SubmissionValidationError

logger = logging.getLogger(__name__)
CONFIG_DIRECTORY = "ingestion_tools/dataset_configs"
TASK_LEASE = timedelta(minutes=15)


def queue_ingestion_pr(job):
    if not settings.DEPOSITION_INGESTION_ENABLED:
        raise SubmissionValidationError("Automatic ingestion PRs are not configured on this server.")
    with transaction.atomic():
        job = DatasetJob.objects.select_for_update().get(pk=job.pk)
        if job.state != "completed":
            raise SubmissionValidationError("Upload must complete before creating an ingestion PR.")
        if job.ingestion_state == "pr_opened":
            return job
        if (
            job.ingestion_state in ("not_started", "opening_pr")
            and job.ingestion_attempt
            and job.updated_at > timezone.now() - TASK_LEASE
        ):
            return job
        attempt = uuid.uuid4().hex
        job.ingestion_state = "not_started"
        job.ingestion_attempt = attempt
        job.ingestion_error = ""
        job.ingestion_branch = f"deposition-{job.dataset.deposition.deposition_id}-dataset-{job.dataset.dataset_id}"
        job.save(
            update_fields=["ingestion_state", "ingestion_attempt", "ingestion_error", "ingestion_branch", "updated_at"]
        )

        def enqueue():
            try:
                async_task(
                    "depositions.tasks.create_ingestion_pr",
                    job.pk,
                    attempt,
                    task_name=f"ingestion_{job.pk}",
                    timeout=600,
                )
            except Exception:
                logger.exception("Could not queue ingestion PR for DatasetJob %s", job.pk)
                finish_attempt(
                    job.pk,
                    attempt,
                    {"ingestion_state": "failed", "ingestion_error": "Could not queue ingestion PR. Retry."},
                )

        transaction.on_commit(enqueue)
    job.refresh_from_db()
    return job


def finish_attempt(job_id, attempt, result):
    DatasetJob.objects.filter(pk=job_id, ingestion_attempt=attempt).update(**result, updated_at=timezone.now())


def _read_uploaded_config(job):
    destination = resolve_sync_destination(cluster=job.cluster_id)
    uri = f"{destination}/{job.dataset.deposition.deposition_id}/{job.dataset.dataset_id}"
    source = urlsplit(uri)
    prefix = source.path.strip("/")
    profile = ["--profile", settings.DEPOSITION_AWS_PROFILE] if settings.DEPOSITION_AWS_PROFILE else []
    ssh = clusterio.get_cluster_ssh_connection(job.cluster_id, auth=clusterio.get_auth_service_user())
    try:

        def aws(*args):
            _, stdout, stderr = ssh.exec_command(shlex.join(["aws", *profile, *args]), timeout=60)
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")
            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError(f"Could not read uploaded ingestion files: {error[-2000:]}")
            return output

        content = aws("s3", "cp", f"{uri}/portal_dataset_config.yaml", "-", "--only-show-errors")
        config = yaml.safe_load(content)
        if not isinstance(config, dict):
            raise ValueError("Uploaded portal_dataset_config.yaml is not a YAML mapping.")
        required = {"version", "standardization_config", "datasets", "depositions", "runs", "voxel_spacings"}
        if missing := required - config.keys():
            raise ValueError(f"Uploaded config is missing sections: {', '.join(sorted(missing))}.")
        standardization = config.get("standardization_config") or {}
        if standardization.get("deposition_id") != job.dataset.deposition.deposition_id:
            raise ValueError("Uploaded config does not match this deposition ID.")
        identifiers = [entry.get("metadata", {}).get("dataset_identifier") for entry in config.get("datasets", [])]
        if identifiers != [job.dataset.dataset_id]:
            raise ValueError("Uploaded config does not match this dataset ID.")
        deposition = job.dataset.deposition
        if deposition.metadata_config_dataset_id == job.dataset.dataset_id:
            metadata = [entry.get("metadata") or {} for entry in config["depositions"]]
            if not any(
                entry.get("deposition_identifier") == deposition.deposition_id
                and isinstance(entry.get("deposition_title"), str)
                and entry["deposition_title"].strip()
                for entry in metadata
            ):
                raise ValueError(
                    "The defining dataset's uploaded config is missing deposition metadata. "
                    "Prepare and upload with a deposition_prep version that supports deposition_metadata."
                )
        relative_prefix = f"{job.dataset.deposition.deposition_id}/{job.dataset.dataset_id}"
        if standardization.get("source_prefix") not in (prefix, relative_prefix):
            raise ValueError("Uploaded config source_prefix does not match the S3 upload location.")
        datamap = standardization.get("run_data_map_file")
        if datamap is not None:
            if (
                not isinstance(datamap, str)
                or not datamap
                or PurePosixPath(datamap).is_absolute()
                or ".." in PurePosixPath(datamap).parts
            ):
                raise ValueError("Uploaded run_data_map_file must be a relative path.")
            aws("s3api", "head-object", "--bucket", source.netloc, "--key", f"{prefix}/{datamap}")
        return content, uri
    finally:
        ssh.close()


class GitHubIngestionPR:
    def __init__(self):
        self.repository = settings.DEPOSITION_INGESTION_GITHUB_REPOSITORY
        self.base_branch = settings.DEPOSITION_INGESTION_GITHUB_BASE_BRANCH
        app_id = settings.DEPOSITION_INGESTION_GITHUB_APP_ID
        key_path = settings.DEPOSITION_INGESTION_GITHUB_KEY_PATH
        if not app_id or not key_path:
            raise ValueError("The ingestion GitHub App ID and private-key path are not configured.")
        try:
            key_bytes = Path(key_path).read_bytes()
        except OSError as error:
            raise ValueError("The ingestion GitHub App key is not provisioned or cannot be read.") from error
        if not key_bytes.strip():
            raise ValueError("The ingestion GitHub App key is not provisioned (empty key file).")
        try:
            key = serialization.load_pem_private_key(key_bytes, password=None)
        except ValueError as error:
            raise ValueError("The ingestion GitHub App key is not a valid PEM private key.") from error

        def encode(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=")

        now = int(time.time())
        header = encode(b'{"alg":"RS256","typ":"JWT"}')
        claims = encode(json.dumps({"iat": now - 60, "exp": now + 540, "iss": app_id}).encode())
        unsigned = header + b"." + claims
        signature = key.sign(unsigned, padding.PKCS1v15(), hashes.SHA256())
        jwt = (unsigned + b"." + encode(signature)).decode()
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {jwt}", "Accept": "application/vnd.github+json"})
        try:
            installation = self.request("GET", "installation")
            response = self.session.request(
                "POST",
                f"https://api.github.com/app/installations/{installation['id']}/access_tokens",
                timeout=30,
                json={
                    "repositories": [self.repository.split("/")[1]],
                    "permissions": {"contents": "write", "pull_requests": "write"},
                },
            )
            response.raise_for_status()
            self.session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
        except Exception:
            self.session.close()
            raise

    def request(self, method, path, *, allow_missing=False, **kwargs):
        response = self.session.request(
            method, f"https://api.github.com/repos/{self.repository}/{path}", timeout=30, **kwargs
        )
        if allow_missing and response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def find(self, branch):
        pulls = self.request(
            "GET",
            "pulls",
            params={"state": "all", "head": f"{self.repository.split('/')[0]}:{branch}", "base": self.base_branch},
        )
        return pulls[0] if pulls else None

    def content(self, filename, ref):
        return self.request("GET", f"contents/{CONFIG_DIRECTORY}/{filename}", params={"ref": ref}, allow_missing=True)

    def create(self, branch, filename, content, *, title, body):
        existing = self.find(branch)
        if existing:
            return existing["html_url"]
        if self.content(filename, self.base_branch):
            raise ValueError(
                f"{filename} already exists on {self.base_branch}; refusing to replace an ingested dataset."
            )
        ref_path = f"git/ref/heads/{quote(branch, safe='/')}"
        if not self.request("GET", ref_path, allow_missing=True):
            base = self.request("GET", f"git/ref/heads/{quote(self.base_branch, safe='/')}")
            self.request("POST", "git/refs", json={"ref": f"refs/heads/{branch}", "sha": base["object"]["sha"]})
        previous = self.content(filename, branch)
        encoded = base64.b64encode(content.encode()).decode()
        if previous is None or "".join(previous.get("content", "").split()) != encoded:
            payload = {"message": title, "content": encoded, "branch": branch}
            if previous:
                payload["sha"] = previous["sha"]
            self.request("PUT", f"contents/{CONFIG_DIRECTORY}/{filename}", json=payload)
        # A previous request may have succeeded before its response was lost.
        existing = self.find(branch)
        if existing:
            return existing["html_url"]
        result = self.request(
            "POST", "pulls", json={"title": title, "body": body, "head": branch, "base": self.base_branch}
        )
        return result["html_url"]


def open_ingestion_pr(job):
    dataset = job.dataset
    branch = job.ingestion_branch
    github = GitHubIngestionPR()
    try:
        content, source = _read_uploaded_config(job)
        digest = hashlib.sha256(content.encode()).hexdigest()
        if job.last_validated_hash and job.last_validated_hash != digest:
            raise ValueError("Uploaded config changed since the previous ingestion PR attempt.")
        if not DatasetJob.objects.filter(pk=job.pk, ingestion_attempt=job.ingestion_attempt).update(
            last_validated_hash=digest
        ):
            raise ValueError("The ingestion PR attempt was superseded.")
        existing = github.find(branch)
        if existing:
            return existing["html_url"]
        return github.create(
            branch,
            f"{dataset.dataset_id}.yaml",
            content,
            title=f"feat: ingest dataset {dataset.dataset_id}",
            body=f"Uploaded by Embrella.\n\nDataset: {dataset.dataset_id}\nDeposition: {dataset.deposition.deposition_id}\n"
            f"Source: `{source}`\n\nThis is the uploaded config, unchanged. Portal CI performs ingestion-schema validation.\n"
            "`run_to_data_map.tsv` and source files remain in the uploaded S3 prefix.",
        )
    finally:
        github.session.close()
