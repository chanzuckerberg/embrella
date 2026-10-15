"""Progress collection stays optional, attempt-scoped, and safe for the public API."""

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from workflow.processors import deposition_progress as reporter

from depositions.models import Dataset, DatasetJob, Deposition
from depositions.serializers import DatasetJobSerializer
from depositions.services import progress


def snapshot(**fields):
    return {"done": 5, "total": 10, "started_at": 100, "updated_at": 110, "initial_done": 0, **fields}


@pytest.mark.django_db
def test_collect_rejects_regressions_and_old_attempts_and_sanitizes_api(monkeypatch):
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS", dataset_id=2)
    job = DatasetJob.objects.create(dataset=ds, state="prep_running", prep_slurm_job_id="123")
    raw = snapshot(
        items=[
            {"label": "/private/source", "done": 1, "total": 1},
            {"label": "Frames", "done": 5, "total": 10, "path": "/private/source"},
        ]
    )
    monkeypatch.setattr(progress, "get_processor", lambda _: SimpleNamespace(get_script_directory=lambda **kw: "/jobs"))
    monkeypatch.setattr(progress.clusterio, "read_remote_file_tail", lambda *a, **kw: json.dumps(raw))
    progress.collect(job, "prep", "bruno", "123", {"username": "service"})
    job.refresh_from_db()
    saved = job.sync_progress
    for fields, attempt in [({"done": 4}, "123"), ({"updated_at": 109}, "123"), ({"done": 6}, "old")]:
        raw.update(fields)
        progress.collect(job, "prep", "bruno", attempt, {"username": "service"})
        job.refresh_from_db()
        assert job.sync_progress == saved
    public = DatasetJobSerializer(job).data["sync_progress"]
    assert public == {"done": 5, "total": 10, "eta": "10s", "items": [{"label": "Frames", "done": 5, "total": 10}]}
    assert "/private" not in json.dumps(public)
    assert "started_at" not in public


@pytest.mark.parametrize(
    "done,total,initial,eta", [(0, 0, 0, None), (1, 1, 0, None), (5, 10, 5, None), (5, 10, 0, "10s")]
)
def test_eta_requires_measured_advancement(done, total, initial, eta):
    assert progress.serialize_progress(snapshot(done=done, total=total, initial_done=initial))["eta"] == eta


@pytest.mark.django_db
def test_missing_progress_never_changes_job_state(monkeypatch):
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    job = DatasetJob.objects.create(dataset=ds, state="push_running", push_slurm_job_id="123")
    monkeypatch.setattr(progress, "get_processor", lambda _: SimpleNamespace(get_script_directory=lambda **kw: "/jobs"))

    def unavailable(*a, **kw):
        raise OSError("unavailable")

    monkeypatch.setattr(progress.clusterio, "read_remote_file_tail", unavailable)
    assert progress.collect(job, "push", "bruno", "123", {"username": "service"}) is None
    job.refresh_from_db()
    assert job.state == "push_running" and job.push_progress is None


def test_reporter_counts_real_staged_files_and_followed_link_bytes(tmp_path):
    import yaml

    source = tmp_path / "source"
    source.mkdir()
    (source / "TiltSeries_Metrics.csv").write_text("Tilt_Series\nPosition_1.mrc\n")
    (source / "Position_1.mrc").write_bytes(b"mrc")
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output_dir": str(tmp_path),
                "datasets": {"ds": {"dataset_id": 2, "sessions": {"session": {"paths": {"aretomo3": str(source)}}}}},
            }
        )
    )
    root, inventory = reporter.prep_inventory(config, "2")
    root.mkdir()
    (root / "session_Position_1_TS.mrc").symlink_to(source / "Position_1.mrc")
    assert reporter.prep_sample(root, inventory, False)["done"] == 1
    assert reporter.prep_sample(root, inventory, True)["summary"] == {"objects": 1, "bytes": 3}
    # AWS uses carriage returns and human-readable byte units.
    assert reporter.upload_sample("Completed 1.0 MiB/4.0 MiB\rCompleted 2.0 MiB/4.0 MiB") == {
        "done": 2 * 1024**2,
        "total": 4 * 1024**2,
    }


@pytest.mark.django_db
def test_syncer_stores_final_summary_on_completion(monkeypatch):
    import workflow.syncers

    from depositions import tasks

    now = timezone.now()
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    job = DatasetJob.objects.create(
        dataset=ds, state="prep_running", prep_slurm_job_id="123", started_at=now - timedelta(seconds=20)
    )
    raw = snapshot(complete=True, done=10, summary={"objects": 10, "bytes": 2048})
    monkeypatch.setattr(progress, "get_processor", lambda _: SimpleNamespace(get_script_directory=lambda **kw: "/jobs"))
    monkeypatch.setattr(progress.clusterio, "read_remote_file_tail", lambda *a, **kw: json.dumps(raw))
    monkeypatch.setattr(tasks, "_job_auth", lambda: {"username": "service"})
    monkeypatch.setattr(
        workflow.syncers,
        "JobStatusSyncer",
        lambda **kw: SimpleNamespace(
            get_job_info_from_sacct=lambda: {"state": "COMPLETED", "exit_code": "0:0"}, is_job_terminal=lambda _: True
        ),
    )
    tasks.run_deposition_job_syncer(job.pk, "prep", "bruno", "123")
    job.refresh_from_db()
    assert job.state == "prep_completed"
    public = DatasetJobSerializer(job).data
    assert public["sync_summary"]["objects"] == 10
    assert public["sync_summary"]["size"] == "2.0 KiB"
    assert public["sync_summary"]["duration"]
    assert public["sync_progress"]["done"] == public["sync_progress"]["total"] == 10


@pytest.mark.parametrize("phase", ["prep", "push"])
def test_generated_scripts_publish_progress_and_preserve_command_failure(tmp_path, phase):
    import os
    import subprocess
    import sys
    from pathlib import Path

    import yaml
    from workflow.processors.deposition_prep.processor import DepositionPrepProcessor
    from workflow.processors.deposition_push.processor import DepositionPushProcessor

    source = tmp_path / "source"
    source.mkdir()
    (source / "TiltSeries_Metrics.csv").write_text("Tilt_Series\nPosition_1.mrc\n")
    (source / "Position_1.mrc").write_text("data")
    output = tmp_path / "staged with spaces"
    config = {
        "output_dir": str(output),
        "datasets": {"ds": {"dataset_id": 2, "sessions": {"session": {"paths": {"aretomo3": str(source)}}}}},
    }
    if phase == "prep":
        script = DepositionPrepProcessor().render_script(
            {
                "output_dir": str(output),
                "config_path": str(output / "config.yaml"),
                "config_yaml": yaml.safe_dump(config),
                "dataset_id": 2,
                "prep_env": "test",
                "run_validate": False,
            },
            SimpleNamespace(cluster_id="bruno"),
        )
        command = 'cryoetportalprep() { mkdir -p "$output_dir/2"; printf data > "$output_dir/2/test.mrc"; return "$command_status"; }'
    else:
        script = DepositionPushProcessor().render_script(
            {
                "staged_dir": str(output),
                "s3_dest": "s3://example/dataset/",
                "prologue": ":",
            },
            SimpleNamespace(cluster_id="bruno"),
        )
        command = (
            'aws() { printf "Completed 2.0 MiB/4.0 MiB\\rCompleted 4.0 MiB/4.0 MiB\\n"; return "$command_status"; }'
        )
    env = {
        **os.environ,
        "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}",
        "SLURM_SUBMIT_DIR": str(tmp_path),
        "SLURM_JOB_ID": "123",
    }
    prefix = "ml() { :; }\nconda() { :; }\n" + command + "\ncommand_status=0\n"
    result = subprocess.run(["bash"], input=prefix + script, text=True, capture_output=True, env=env, timeout=20)
    assert result.returncode == 0, result.stderr
    sample = json.loads((tmp_path / f"deposition-{phase}-123.progress.json").read_text())
    assert sample["complete"] is True and sample["done"] == sample["total"]
    if phase == "prep":
        assert sample["summary"] == {"objects": 1, "bytes": 4}
    else:
        assert sample["done"] == 4 * 1024**2
    result = subprocess.run(
        ["bash"],
        input=prefix.replace("command_status=0", "command_status=9") + script,
        text=True,
        capture_output=True,
        env={**env, "SLURM_JOB_ID": "124"},
        timeout=20,
    )
    assert result.returncode == 9, result.stderr
