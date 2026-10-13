import pytest
from processes.models import PipeExecution, SyncerProcess
from workflow.views.job_api import _get_syncer_status_for_job

JOB = "14017"


@pytest.mark.django_db
def test_cancelled_job_allows_syncer_rerun():
    # A cancelled job's syncer never reports back; it must still be re-runnable.
    SyncerProcess.objects.create(
        job_id=JOB,
        syncer_type="AretomoSyncer",
        session_name="26oct07a",
        run_id="run001",
        status="running",
    )

    status = _get_syncer_status_for_job(JOB, PipeExecution(job_id=JOB, status="cancelled"))

    assert status["can_rerun"] is True
