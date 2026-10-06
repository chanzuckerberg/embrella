"""Tests for the deposition job launcher."""

import pytest

from depositions.services import launch


class FakeProcessor:
    def __init__(self):
        self.rendered = None

    def render_script(self, params, run_context):
        self.rendered = (params, run_context)
        return "#!/bin/bash\necho hi"

    def get_script_directory(self, cluster):
        return f"/scripts/{cluster}"


class FakeSubmitter:
    output = "Submitted batch job 98765"
    error = ""
    instances = []

    def __init__(self, cluster_id, auth, remote_script_dir):
        self.cluster_id = cluster_id
        self.auth = auth
        self.remote_script_dir = remote_script_dir
        self.calls = []
        FakeSubmitter.instances.append(self)

    def connect(self):
        self.calls.append("connect")

    def run_script(self, *, script_content, job_name):
        self.calls.append(("run", job_name, script_content))
        return type(self).output, type(self).error

    def close(self):
        self.calls.append("close")


@pytest.fixture
def proc(monkeypatch):
    processor = FakeProcessor()
    FakeSubmitter.instances = []
    FakeSubmitter.output = "Submitted batch job 98765"
    monkeypatch.setattr(launch, "get_processor", lambda name: processor)
    monkeypatch.setattr(launch, "RemoteJobSubmitter", FakeSubmitter)
    return processor


def test_returns_parsed_job_id(proc):
    job_id = launch.launch_deposition_job(
        processor_name="deposition-prep", params={"output_dir": "/o"}, cluster_id="bruno", job_name="dep_prep_1"
    )
    assert job_id == "98765"


def test_renders_with_cluster_context(proc):
    launch.launch_deposition_job(processor_name="deposition-prep", params={"x": 1}, cluster_id="czii", job_name="j")
    params, ctx = proc.rendered
    assert params == {"x": 1}
    assert ctx.cluster_id == "czii"


def test_submits_under_job_name_and_cluster(proc):
    launch.launch_deposition_job(processor_name="deposition-push", params={}, cluster_id="bruno", job_name="dep_push_2")
    sub = FakeSubmitter.instances[-1]
    assert sub.cluster_id == "bruno"
    assert sub.remote_script_dir == "/scripts/bruno"
    assert ("run", "dep_push_2", "#!/bin/bash\necho hi") in sub.calls


def test_raises_when_job_id_missing_and_still_closes(proc, monkeypatch):
    monkeypatch.setattr(FakeSubmitter, "output", "sbatch: error: boom")
    with pytest.raises(launch.LaunchError, match="Could not parse SLURM job id"):
        launch.launch_deposition_job(processor_name="deposition-prep", params={}, cluster_id="bruno", job_name="j")
    assert "close" in FakeSubmitter.instances[-1].calls
