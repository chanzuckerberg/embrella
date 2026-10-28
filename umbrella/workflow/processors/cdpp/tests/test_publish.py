"""publish_aretomo3: the refined reconstruction as an Embrella AreTomo3 run, converted for review after the pipeline."""

from unittest.mock import MagicMock, patch

import pytest
from processes.models import JobLog, PipeExecution, ProcPlan, ProcRun

from workflow.execution import PipelineExecutor
from workflow.processors.cdpp.processor import PUBLISH_VARIANT, CdppProcessor

from .conftest import PLAN, PUBLISH_PLAN, ROOT, SESSION

PARAMS = {"aretomo_run": "run001", "preset": "insitu_import", "refined_pixel_size": 10.4}
PUBLISH = {**PARAMS, "publish_aretomo3": True}
PUBLISHED_DIR = f"{ROOT}/aretomo3/{SESSION}/run002"
FLAG = f"--publish-aretomo3 {PUBLISH_VARIANT}"
USER_AUTH = {"username": "launcher", "pkey": "user-key"}


@pytest.fixture
def input_run(cdpp_plans, test_msi_session):
    """The AreTomo3 run the pipeline imports: the published run must not take its number."""
    return ProcRun.objects.create(
        name="run001", proc_plan=ProcPlan.objects.get(name="czii-live"), msi_session=test_msi_session
    )


# Launch option


@pytest.mark.django_db
def test_script_passes_the_option_only_when_set(cdpp_plans, cdpp_context):
    reservation = {"trees": {"aretomo3": {"run": "run002", "dir": PUBLISHED_DIR}}}
    processor = CdppProcessor()

    on = processor.render_script({**PUBLISH, "_reserved_runs": reservation}, cdpp_context)
    off = processor.render_script({**PARAMS, "publish_aretomo3": False}, cdpp_context)

    assert f"    {FLAG} \\" in on
    assert f"    --tree aretomo3={PUBLISHED_DIR} \\" in on
    assert "--publish-aretomo3" not in off
    assert "--publish-aretomo3" not in processor.render_script(PARAMS, cdpp_context)


@pytest.mark.django_db
def test_reservation_has_the_aretomo3_tree_only_when_set(fake_cluster, cdpp_context, input_run):
    fake_cluster.dirs = {"aretomo3": ["run001", "run002"]}  # run002 exists on disk only
    processor = CdppProcessor()

    off = processor.reserve_runs(cdpp_context, PARAMS)
    on = processor.reserve_runs(cdpp_context, PUBLISH)

    assert "aretomo3" not in off["trees"]
    assert on["pipeline_fingerprint"] == PUBLISH_PLAN["fingerprint"]
    assert on["trees"]["aretomo3"] == {
        "plan": "czii-live",
        "run": "run003",
        "dir": f"{ROOT}/aretomo3/{SESSION}/run003",
        "fingerprint": PUBLISH_PLAN["trees"]["aretomo3"]["fingerprint"],
        "reused": False,
    }
    # Planning and the job share one argument list, so the flag is planned exactly as the job passes it.
    plan_off, plan_on = fake_cluster.plan_commands
    assert "--publish-aretomo3" not in plan_off
    assert f"{FLAG} --plan-only" in plan_on
    assert set(on["trees"]) == set(PLAN["trees"]) | {"aretomo3"}


# Submission


def _execute(cdpp_step, cdpp_run, user, job_id, conversion_output="Submitted batch job 4300", params=PUBLISH):
    submitter = MagicMock()
    submitter.run_script.return_value = (f"Submitted batch job {job_id}", "")
    submitter.last_script_path = f"/scripts/{job_id}.sh"
    conversion = MagicMock()
    conversion.run_script.return_value = (conversion_output, "")
    conversion.last_script_path = "/scripts/convert.sh"
    with (
        patch("workflow.execution.RemoteJobSubmitter", return_value=submitter),
        patch("workflow.processors.cdpp.processor.RemoteJobSubmitter", return_value=conversion) as conversion_class,
        patch("common.clusterio.get_auth_for_user", return_value=(USER_AUTH, None)) as auth_for_user,
        patch("processes.tasks.start_job_status_syncer") as status_syncer,
        patch.object(CdppProcessor, "_start_syncer_task") as output_syncers,
    ):
        result = PipelineExecutor().execute_pipe(
            pipe_in_plan=cdpp_step,
            proc_run=cdpp_run,
            user=user,
            parameters=dict(params),
            auth=USER_AUTH,
            cluster_id="czii",
        )
    return {
        "result": result,
        "conversion": conversion,
        "conversion_class": conversion_class,
        "auth_for_user": auth_for_user,
        "status_syncer": status_syncer,
        "output_syncers": output_syncers,
    }


def _published_execution():
    return PipeExecution.objects.select_related("proc_run").get(
        proc_run__proc_plan__name="czii-live", proc_run__name="run002"
    )


@pytest.mark.django_db
def test_execute_submits_the_conversion_after_the_cdpp_job(fake_cluster, cdpp_step, cdpp_run, test_user, input_run):
    run = _execute(cdpp_step, cdpp_run, test_user, "4242")

    # Submitted as the launching user, held until the cdpp job succeeds.
    run["auth_for_user"].assert_called_once_with(test_user, "czii")
    assert run["conversion_class"].call_args.kwargs["auth"] == USER_AUTH
    script = run["conversion"].run_script.call_args.kwargs["script_content"]
    for line in (
        "#SBATCH --dependency=afterok:4242",
        "#SBATCH --kill-on-invalid-dep=yes",
        f"#SBATCH -o {PUBLISHED_DIR}/JOB%j_convert.out",
        f"run_dir={PUBLISHED_DIR}",
        'for vol in "${run_dir}"/vol001/*_Vol.mrc; do',
    ):
        assert line in script
    assert "vol003" not in script.split("set -euo pipefail")[1]

    # The published run follows its conversion job, which is recorded in its _cdpp block.
    published = _published_execution()
    assert published.job_id == "4300"
    assert published.script_content == script
    assert published.parameters["_cdpp"]["tree"] == "aretomo3"
    assert published.parameters["_cdpp"]["cdpp_job_id"] == "4242"
    assert published.parameters["_cdpp"]["conversion_job_id"] == "4300"
    assert published.parameters["_cdpp"]["dir"] == PUBLISHED_DIR
    assert JobLog.objects.get(job_id="4300").user == test_user
    # The other trees stay on the cdpp job.
    assert PipeExecution.objects.filter(job_id="4242").count() == 1 + len(PLAN["trees"])

    assert {call.kwargs["job_id"] for call in run["status_syncer"].call_args_list} == {"4242", "4300"}
    syncers = {call.kwargs["syncer_class_path"]: call.kwargs for call in run["output_syncers"].call_args_list}
    aretomo = syncers["workflow.processors.aretomo3.syncer.AretomoSyncer"]
    assert aretomo["job_id"] == "4300"
    assert aretomo["run_context"].run_number == "run002"
    assert aretomo["base_path"] == f"{ROOT}/aretomo3"
    assert syncers["workflow.processors.cdpp.syncer.CdppSyncer"]["job_id"] == "4242"


@pytest.mark.django_db
def test_failed_conversion_submission_leaves_the_run_on_the_cdpp_job(
    fake_cluster, cdpp_step, cdpp_run, test_user, input_run
):
    run = _execute(cdpp_step, cdpp_run, test_user, "4242", conversion_output="sbatch: error: invalid partition")

    published = _published_execution()
    assert published.job_id == "4242"
    assert "no job id" in published.parameters["_cdpp"]["conversion_error"]
    assert [call.kwargs["job_id"] for call in run["status_syncer"].call_args_list] == ["4242"]
    assert [call.kwargs["syncer_class_path"] for call in run["output_syncers"].call_args_list] == [
        "workflow.processors.cdpp.syncer.CdppSyncer"
    ]


@pytest.mark.django_db
def test_relaunch_converts_the_same_published_run_again(fake_cluster, cdpp_step, cdpp_run, test_user, input_run):
    _execute(cdpp_step, cdpp_run, test_user, "5001", conversion_output="Submitted batch job 5101")

    run = _execute(cdpp_step, cdpp_run, test_user, "5002", conversion_output="Submitted batch job 5102")

    published = _published_execution()
    assert published.job_id == "5102"
    assert published.parameters["_attempts"][-1]["job_id"] == "5101"
    assert "#SBATCH --dependency=afterok:5002" in run["conversion"].run_script.call_args.kwargs["script_content"]
    assert ProcRun.objects.filter(proc_plan__name="czii-live").count() == 2
