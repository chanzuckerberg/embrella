"""cluster_id_for_run scopes by processor so a shared run name resolves unambiguously."""

import pytest

from processes.models import Pipe, PipeExecution, PipeInPlan, ProcSoftware
from processes.services.cluster_resolver import cluster_id_for_run


@pytest.mark.django_db
def test_cluster_lookup_scopes_by_processor_class(test_proc_run, test_pipe_in_plan):
    # Same run name, two processors, two clusters.
    PipeExecution.objects.create(
        proc_run=test_proc_run, pipe_in_plan=test_pipe_in_plan, parameters={"cluster_id": "aretomo-cluster"}
    )
    other = PipeInPlan.objects.create(
        plan=test_proc_run.proc_plan,
        pipe=Pipe.objects.create(
            name="denoise_pipe",
            software=ProcSoftware.objects.create(name="denoise_sw", version="1.0.0", processor_class="denoiset"),
        ),
        step=2,
        name="denoise_step",
    )
    PipeExecution.objects.create(
        proc_run=test_proc_run, pipe_in_plan=other, parameters={"cluster_id": "denoise-cluster"}
    )

    name, run = test_proc_run.msi_session.name, test_proc_run.name
    assert cluster_id_for_run(name, run, processor_class="test_processor") == "aretomo-cluster"
    assert cluster_id_for_run(name, run, processor_class="denoiset") == "denoise-cluster"


@pytest.mark.django_db
def test_unscoped_lookup_returns_the_newest_execution(test_proc_run, test_pipe_in_plan):
    PipeExecution.objects.create(
        proc_run=test_proc_run, pipe_in_plan=test_pipe_in_plan, parameters={"cluster_id": "older-cluster"}
    )
    newer = PipeInPlan.objects.create(
        plan=test_proc_run.proc_plan,
        pipe=Pipe.objects.create(name="newer_pipe", software=test_pipe_in_plan.pipe.software),
        step=2,
        name="newer_step",
    )
    PipeExecution.objects.create(proc_run=test_proc_run, pipe_in_plan=newer, parameters={"cluster_id": "newer-cluster"})
    assert cluster_id_for_run(test_proc_run.msi_session.name, test_proc_run.name) == "newer-cluster"


@pytest.mark.django_db
def test_scoped_miss_returns_the_fallback_and_warns(test_proc_run, test_pipe_in_plan, caplog):
    # Only a test_processor execution exists; a denoiset lookup must fall through to the default.
    PipeExecution.objects.create(
        proc_run=test_proc_run, pipe_in_plan=test_pipe_in_plan, parameters={"cluster_id": "aretomo-cluster"}
    )
    name, run = test_proc_run.msi_session.name, test_proc_run.name
    with caplog.at_level("WARNING"):
        assert cluster_id_for_run(name, run, default="fallback", processor_class="denoiset") == "fallback"
    assert "No denoiset execution with a cluster_id" in caplog.text
