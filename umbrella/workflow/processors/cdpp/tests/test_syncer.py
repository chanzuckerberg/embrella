"""CdppSyncer: reads the job's progress.json and logs a one-line summary."""

import json

import pytest
from processes.models import PipeExecution, PipeInPlan, ProcRun, SyncerLog, SyncerProcess

from workflow.processors.cdpp.syncer import CdppSyncer, summarize_progress

from .conftest import CDPP_DIR, PROGRESS, ROOT, SESSION

JOB = "31337"


def test_summarize_progress():
    message, metadata = summarize_progress(json.loads(PROGRESS))

    assert message == "Pipeline progress: 5/10 done, 1 running, 1 queued, 1 failed (warp_metadata_create)"
    assert metadata["summary"]["total"] == 10
    assert metadata["failed_steps"] == ["warp_metadata_create"]
    assert metadata["driver_job_id"] == "31337"


@pytest.fixture
def syncer(cdpp_plans, cdpp_step, cdpp_run, test_msi_session):
    """A CdppSyncer for a job that also backs a tree run's execution."""
    tree_plan = cdpp_plans["czii-isonet2"]
    tree_run = ProcRun.objects.create(name="run001", proc_plan=tree_plan, msi_session=test_msi_session)
    PipeExecution.objects.create(
        proc_run=tree_run, pipe_in_plan=PipeInPlan.objects.get(plan=tree_plan), job_id=JOB, parameters={}
    )
    PipeExecution.objects.create(
        proc_run=cdpp_run, pipe_in_plan=cdpp_step, job_id=JOB, parameters={"cluster_id": "czii"}
    )

    syncer = CdppSyncer(base_path=f"{ROOT}/cdpp", log_dir="/tmp")
    syncer.job_id = JOB
    syncer.setup(run_id="run001", session_name=SESSION, cluster_id="czii")
    return syncer


@pytest.mark.django_db
def test_logs_progress_against_the_cdpp_execution(monkeypatch, syncer, cdpp_run):
    reads = []
    monkeypatch.setattr(
        "common.clusterio.read_remote_file", lambda cluster_id, path: reads.append((cluster_id, path)) or PROGRESS
    )

    syncer.sync_results()

    assert reads == [("czii", f"{CDPP_DIR}/nextflow/progress.json")]
    entry = SyncerLog.objects.get(job_id=JOB, action_type="sync_complete")
    assert entry.message.startswith("Pipeline progress: 5/10 done")
    assert entry.metadata["failed_steps"] == ["warp_metadata_create"]
    assert entry.pipe_execution.proc_run == cdpp_run
    assert SyncerProcess.objects.get(job_id=JOB).pipe_execution.proc_run == cdpp_run


@pytest.mark.django_db
def test_missing_progress_is_a_warning(monkeypatch, syncer):
    def missing(cluster_id, path):
        raise FileNotFoundError(path)

    monkeypatch.setattr("common.clusterio.read_remote_file", missing)

    syncer.sync_results()

    entry = SyncerLog.objects.get(job_id=JOB, action_type="warning")
    assert "No progress yet" in entry.message
