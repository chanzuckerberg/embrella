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
@pytest.mark.parametrize("phase", ["prep", "push"])
def test_collect_rejects_regressions_and_old_attempts_and_sanitizes_api(monkeypatch, phase):
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS", dataset_id=2)
    job = DatasetJob.objects.create(dataset=ds, state=f"{phase}_running", **{f"{phase}_slurm_job_id": "123"})
    field = "sync_progress" if phase == "prep" else "push_progress"
    raw = snapshot(
        items=[
            {"label": "/private/source", "done": 1, "total": 1},
            {"label": "Frames", "done": 5, "total": 10, "path": "/private/source"},
        ]
    )
    monkeypatch.setattr(progress, "get_processor", lambda _: SimpleNamespace(get_script_directory=lambda **kw: "/jobs"))
    monkeypatch.setattr(progress.clusterio, "read_remote_file_tail", lambda *a, **kw: json.dumps(raw))
    progress.collect(job, phase, "cluster-a", "123", {"username": "service"})
    job.refresh_from_db()
    saved = getattr(job, field)
    for fields, attempt in [({"done": 4}, "123"), ({"updated_at": 109}, "123"), ({"done": 6}, "old")]:
        raw.update(fields)
        progress.collect(job, phase, "cluster-a", attempt, {"username": "service"})
        job.refresh_from_db()
        assert getattr(job, field) == saved
    public = DatasetJobSerializer(job).data[field]
    expected = {"done": 5, "total": 10, "eta": "10s"}
    if phase == "prep":
        expected["items"] = [{"label": "Frames", "done": 5, "total": 10}]
    assert public == expected
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
    assert progress.collect(job, "push", "cluster-a", "123", {"username": "service"}) is None
    job.refresh_from_db()
    assert job.state == "push_running" and job.push_progress is None


def test_reporter_counts_real_staged_files_and_followed_link_bytes(tmp_path):
    import yaml

    source = tmp_path / "source"
    source.mkdir()
    (source / "TiltSeries_Metrics.csv").write_text("Tilt_Series\nPosition_1.mrc\n")
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
    tiltseries = next(
        item for item in reporter.prep_sample(root, inventory, True)["items"] if item["label"] == "Tilt series"
    )
    assert tiltseries == {"label": "Tilt series", "done": 0, "total": 1}
    (source / "Position_1.mrc").write_bytes(b"mrc")
    assert reporter.prep_sample(root, inventory, False)["done"] == 1
    assert reporter.prep_sample(root, inventory, True)["summary"] == {"objects": 1, "bytes": 3}


def test_finished_sync_snapshot_excludes_validation_time():
    raw = snapshot(complete=True, done=10)
    public = progress.serialize_progress(raw)
    assert public["completed_at"] == "1970-01-01T00:01:50+00:00"
    job = SimpleNamespace(
        sync_summary={"objects": 10, "bytes": 2048},
        sync_progress=raw,
        started_at=timezone.datetime.fromtimestamp(100, timezone.get_default_timezone()),
        prep_completed_at=timezone.datetime.fromtimestamp(170, timezone.get_default_timezone()),
    )
    assert progress.serialize_summary(job)["duration"] == "10s"


@pytest.mark.parametrize("estimated", ["", "~"])
def test_upload_progress_reads_latest_aws_total(estimated):
    text = f"Completed 1.0 MiB/{estimated}4.0 MiB\rCompleted 2.0 MiB/{estimated}4.0 MiB (31.0 MiB/s)"
    assert reporter.upload_sample(text) == {
        "done": 2 * 1024**2,
        "total": 4 * 1024**2,
        "estimated": bool(estimated),
    }


@pytest.mark.parametrize("separator", ["\n", "\r", "\r\n"])
def test_upload_reporter_counts_completed_files_across_reads(tmp_path, monkeypatch, separator):
    source = tmp_path / "upload.log"
    source.write_bytes(
        (
            f"(calculating...)Completed 2.0 MiB/~4.0 MiB (1.0 MiB/s) with ~1 file(s) remaining{separator}"
            f"upload: one.mrc to s3://example/one.mrc{separator}up"
        ).encode()
    )
    path = tmp_path / "progress.json"
    samples = []
    monkeypatch.setattr(reporter, "write_snapshot", lambda _, sample: samples.append(sample.copy()))

    def advance(_):
        if len(samples) == 1:
            with source.open("ab") as handle:
                handle.write(
                    (
                        f"load: two.mrc to s3://example/two.mrc{separator}"
                        f"Completed 4.0 MiB/4.0 MiB (1.0 MiB/s) with 0 file(s) remaining{separator}"
                    ).encode()
                )
        else:
            path.with_suffix(".json.done").touch()

    monkeypatch.setattr(reporter.time, "sleep", advance)
    reporter.report("push", str(path), str(source))
    assert samples[0]["objects"] == {"done": 1, "total": 2, "estimated": True}
    assert samples[1]["objects"] == samples[2]["objects"] == {"done": 2, "total": 2, "estimated": False}


@pytest.mark.django_db
@pytest.mark.parametrize("estimated", [False, True])
def test_upload_counts_and_elapsed_are_collected_and_serialized(monkeypatch, estimated):
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    job = DatasetJob.objects.create(dataset=ds, state="push_running", push_slurm_job_id="123")
    objects = {"done": 2, "total": 4, "estimated": estimated}
    raw = snapshot(estimated=estimated, objects={**objects, "path": "/private/source"})
    monkeypatch.setattr(progress, "get_processor", lambda _: SimpleNamespace(get_script_directory=lambda **kw: "/jobs"))
    monkeypatch.setattr(progress.clusterio, "read_remote_file_tail", lambda *a, **kw: json.dumps(raw))
    progress.collect(job, "push", "cluster-a", "123", {"username": "service"})
    job.refresh_from_db()
    public = DatasetJobSerializer(job).data["push_progress"]
    assert public == {
        "done": 5,
        "total": 10,
        "eta": None if estimated else "10s",
        "elapsed": "10s",
        "estimated": estimated,
        "objects": objects,
    }


@pytest.mark.parametrize("mdoc_suffix", [".mdoc", ".mrc.mdoc"])
def test_prep_inventory_matches_cli_mdoc_support(tmp_path, mdoc_suffix):
    import yaml

    source = tmp_path / "source"
    source.mkdir()
    (source / "TiltSeries_Metrics.csv").write_text("Tilt_Series\nPosition_1.mrc\n")
    mdoc_dir = tmp_path / "mdoc"
    mdoc_dir.mkdir()
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (mdoc_dir / f"Position_1{mdoc_suffix}").write_bytes(
        b"# non-UTF-8 note: \xff\nSubFramePath = X:\\data\\frame_1.tif\n"
    )
    (frames_dir / "frame_1.tif").write_bytes(b"f")
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output_dir": str(tmp_path),
                "datasets": {
                    "ds": {
                        "dataset_id": 2,
                        "sessions": {
                            "session": {
                                "paths": {"aretomo3": str(source), "mdoc": str(mdoc_dir), "frames": str(frames_dir)}
                            }
                        },
                    }
                },
            }
        )
    )
    _, inventory = reporter.prep_inventory(config, "2")
    # Mirrors deposition_prep's find_source_mdoc.
    assert inventory["session_Position_1.mdoc"] == "Metadata"
    assert inventory["session_Position_1/session_frame_1.tif"] == "Frames"


# Expected staged names mirror deposition_prep SYMLINK_TYPES; the mapping is confirmed against the CLI source, not here.
def test_prep_inventory_matches_expected_staged_names(tmp_path):
    import yaml

    source = tmp_path / "source"
    source.mkdir()
    (source / "TiltSeries_Metrics.csv").write_text("Tilt_Series\nPosition_1.mrc\n")
    staged_names = {
        "Position_1.aln": "session_Position_1.aln",
        "Position_1_CTF.txt": "session_Position_1_CTFFIND_format_CTF.txt",
        "Position_1.mrc": "session_Position_1_TS.mrc",
        "Position_1_Vol.mrc": "session_Position_1_dctf_Vol.mrc",
    }
    for name in staged_names:
        (source / name).write_bytes(b"data")
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output_dir": str(tmp_path),
                "datasets": {
                    "ds": {
                        "dataset_id": 2,
                        "sessions": {"session": {"paths": {"aretomo3": str(source), "dctf_vol": str(source)}}},
                    }
                },
            }
        )
    )
    root, inventory = reporter.prep_inventory(config, "2")
    root.mkdir()
    for name, staged in staged_names.items():
        (root / staged).symlink_to(source / name)
    items = {item["label"]: item for item in reporter.prep_sample(root, inventory, False)["items"]}
    for label in ("Alignment", "CTF", "Tilt series", "Tomograms"):
        assert items[label] == {"label": label, "done": 1, "total": 1}


@pytest.mark.django_db
@pytest.mark.parametrize("phase", ["prep", "push"])
def test_syncer_preserves_final_progress_and_sync_summary(monkeypatch, phase):
    import workflow.syncers

    from depositions import tasks

    now = timezone.now()
    dep = Deposition.objects.create(title="Dep")
    ds = Dataset.objects.create(deposition=dep, title="DS")
    job = DatasetJob.objects.create(
        dataset=ds,
        state=f"{phase}_running",
        started_at=now - timedelta(seconds=20),
        **{f"{phase}_slurm_job_id": "123"},
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
    tasks.run_deposition_job_syncer(job.pk, phase, "cluster-a", "123")
    job.refresh_from_db()
    assert job.state == ("prep_completed" if phase == "prep" else "completed")
    public = DatasetJobSerializer(job).data
    if phase == "prep":
        assert job.sync_progress["complete"] is True
        assert public["sync_summary"]["objects"] == 10
        assert public["sync_summary"]["size"] == "2.0 KiB"
        assert public["sync_summary"]["duration"]
    field = "sync_progress" if phase == "prep" else "push_progress"
    assert public[field]["done"] == public[field]["total"] == 10


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
            },
            SimpleNamespace(cluster_id="cluster-a"),
        )
        command = """cryoetportalprep() {
          mkdir -p "$output_dir/2"
          printf data > "$output_dir/2/test.mrc"
          echo 'datasets: [{metadata: {dataset_identifier: 2}}]' > "$output_dir/2/portal_dataset_config.yaml"
          return "$command_status"
        }"""
    else:
        script = DepositionPushProcessor().render_script(
            {
                "staged_dir": str(output),
                "s3_dest": "s3://example/datasets/10001/20002/",
                "prologue": ":",
            },
            SimpleNamespace(cluster_id="cluster-a"),
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
        assert sample["summary"] == {
            "objects": 2,
            "bytes": 4 + (output / "2" / "portal_dataset_config.yaml").stat().st_size,
        }
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
