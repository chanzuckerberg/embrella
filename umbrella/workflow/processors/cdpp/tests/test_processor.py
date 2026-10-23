"""cdpp processor: planning and run reservation, the driver script, and the per-tree records."""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from processes.models import PipeExecution, PipeInPlan, ProcPlan, ProcRun

from workflow.execution import PipelineExecutor
from workflow.processors import get_processor
from workflow.processors.cdpp.processor import RESERVED_PLACEHOLDER, CdppProcessor, parse_overrides

from .conftest import CDPP_DIR, PLAN, ROOT, SESSION

FINGERPRINTS = {name: tree["fingerprint"] for name, tree in PLAN["trees"].items()}
PARAMS = {
    "aretomo_run": "run001",
    "preset": "insitu_import",
    "refined_pixel_size": 10.4,
    "config_overrides": "isonet2.epochs=50\n# a comment\n",
}


def _tree_run(plan_name, session, name, fingerprint=None, job_id="100"):
    """A tree run, optionally with an execution that recorded a cdpp tree fingerprint."""
    plan = ProcPlan.objects.get(name=plan_name)
    run = ProcRun.objects.create(name=name, proc_plan=plan, msi_session=session)
    if fingerprint:
        PipeExecution.objects.create(
            proc_run=run,
            pipe_in_plan=PipeInPlan.objects.filter(plan=plan).first(),
            status="completed",
            job_id=job_id,
            parameters={"_cdpp": {"fingerprint": fingerprint}},
        )
    return run


# Parameters


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", []),
        ("a.b=1", ["a.b=1"]),
        ("a.b=1\n\n# note\nc=[1, 2]", ["a.b=1", "c=[1, 2]"]),
        ("a.b=1; c.d=x", ["a.b=1", "c.d=x"]),
    ],
)
def test_parse_overrides(text, expected):
    assert parse_overrides(text) == expected


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({}, None),
        ({"aretomo_run": "../aretomo3"}, "aretomo_run"),
        ({"aretomo_run": ""}, "aretomo_run"),
        ({"refined_pixel_size": 0}, "refined_pixel_size"),
        ({"config_overrides": "isonet2.epochs"}, "dotted.key=value"),
        ({"config_overrides": "bad key=1"}, "dotted.key=value"),
    ],
)
def test_validate_parameters(overrides, error):
    errors = CdppProcessor().validate_parameters({**PARAMS, **overrides})

    if error is None:
        assert errors == []
    else:
        assert any(error in message for message in errors)


# Planning and reservation


@pytest.mark.django_db
def test_reserve_reuses_matching_trees_and_allocates_the_rest(fake_cluster, cdpp_context, test_msi_session):
    _tree_run("czii-miss-alignment", test_msi_session, "run001", fingerprint="older-parameters")
    _tree_run("czii-miss-alignment", test_msi_session, "run002", fingerprint=FINGERPRINTS["miss_alignment"])
    _tree_run("czii-isonet2", test_msi_session, "run001", fingerprint="older-parameters")
    fake_cluster.dirs = {"isonet2": ["run004"]}  # created outside Embrella

    reservation = CdppProcessor().reserve_runs(cdpp_context, PARAMS)

    assert reservation["pipeline_fingerprint"] == PLAN["fingerprint"]
    assert reservation["trees"] == {
        "miss_alignment": {
            "plan": "czii-miss-alignment",
            "run": "run002",
            "dir": f"{ROOT}/miss_alignment/{SESSION}/run002",
            "fingerprint": FINGERPRINTS["miss_alignment"],
            "reused": True,
        },
        "isonet2": {
            "plan": "czii-isonet2",
            "run": "run005",
            "dir": f"{ROOT}/isonet2/{SESSION}/run005",
            "fingerprint": FINGERPRINTS["isonet2"],
            "reused": False,
        },
        "copick": {
            "plan": "czii-copick",
            "run": "run001",
            "dir": f"{ROOT}/copick/{SESSION}/run001",
            "fingerprint": FINGERPRINTS["copick"],
            "reused": False,
        },
    }
    assert ProcRun.objects.filter(proc_plan__name="czii-isonet2", name="run005").exists()

    (command,) = fake_cluster.plan_commands
    assert "conda activate /hpc/projects/group.czii/conda_environments/cdpp" in command
    assert f"--aretomo3-run {ROOT}/aretomo3/{SESSION}/run001" in command
    assert f"--output-dir {CDPP_DIR}" in command
    assert "--refined-pixel-size 10.4 --set isonet2.epochs=50 --plan-only" in command


@pytest.mark.django_db
def test_release_deletes_only_created_runs(fake_cluster, cdpp_context, test_msi_session):
    _tree_run("czii-miss-alignment", test_msi_session, "run002", fingerprint=FINGERPRINTS["miss_alignment"])
    processor = CdppProcessor()
    reservation = processor.reserve_runs(cdpp_context, PARAMS)

    processor.release_runs(cdpp_context, reservation)

    remaining = set(ProcRun.objects.exclude(proc_plan__name="czii-cdpp").values_list("proc_plan__name", "name"))
    assert remaining == {("czii-miss-alignment", "run002")}


@pytest.mark.django_db
def test_unknown_tree_is_refused(fake_cluster, cdpp_context):
    fake_cluster.plan = {**PLAN, "trees": {**PLAN["trees"], "mystery": {"fingerprint": "f"}}}

    with pytest.raises(ValueError, match="mystery"):
        CdppProcessor().reserve_runs(cdpp_context, PARAMS)

    assert not ProcRun.objects.exclude(proc_plan__name="czii-cdpp").exists()


@pytest.mark.django_db
def test_trees_no_step_writes_are_skipped(fake_cluster, cdpp_context):
    # A preset trimmed with overrides: no step writes isonet2 or copick, so the plan has no fingerprint for them.
    trees = PLAN["trees"]
    fake_cluster.plan = {
        **PLAN,
        "trees": {
            **trees,
            "isonet2": {**trees["isonet2"], "fingerprint": None},
            "copick": {**trees["copick"], "fingerprint": ""},
        },
    }
    processor = CdppProcessor()

    reservation = processor.reserve_runs(cdpp_context, PARAMS)

    assert set(reservation["trees"]) == {"miss_alignment"}
    assert set(ProcRun.objects.exclude(proc_plan__name="czii-cdpp").values_list("proc_plan__name", flat=True)) == {
        "czii-miss-alignment"
    }
    script = processor.render_script({**PARAMS, "_reserved_runs": reservation}, cdpp_context)
    assert "--tree miss_alignment=" in script
    assert "--tree isonet2=" not in script
    assert "--tree copick=" not in script


@pytest.mark.django_db
def test_failed_planning_reports_the_error(fake_cluster, cdpp_context):
    fake_cluster.plan = None
    fake_cluster.err = "FileNotFoundError: AreTomo3_Session.json"

    with pytest.raises(ValueError, match="AreTomo3_Session.json"):
        CdppProcessor().reserve_runs(cdpp_context, PARAMS)


# Script


@pytest.mark.django_db
def test_preview_shows_placeholders_and_never_plans(monkeypatch, cdpp_step, cdpp_run, test_user):
    monkeypatch.setattr("common.clusterio.get_cluster_ssh_connection", MagicMock(side_effect=AssertionError("SSH")))

    script = PipelineExecutor().preview(
        pipe_in_plan=cdpp_step, proc_run=cdpp_run, user=test_user, parameters={"aretomo_run": "run001"}
    )

    assert f"--tree <tree>={RESERVED_PLACEHOLDER}" in script
    assert "Preview: the tool trees" in script
    for line in (
        "#SBATCH --partition=cpu",
        "#SBATCH --cpus-per-task=2",
        "#SBATCH --mem=8G",
        "#SBATCH --time=7-00:00:00",
        f"#SBATCH -o {CDPP_DIR}/JOB%j_cdpp.out",
        f"#SBATCH -e {CDPP_DIR}/JOB%j_cdpp.err",
        "umask 0002",
        "conda activate /hpc/projects/group.czii/conda_environments/cdpp",
        "set -euo pipefail",
        f"    --aretomo3-run {ROOT}/aretomo3/{SESSION}/run001 \\",
        "    --preset insitu_import \\",
        "    --refined-pixel-size 10.4 \\",
    ):
        assert line in script
    # The CLI replaces the batch shell (scancel's TERM reaches it) and writes progress.json itself.
    assert script.rstrip().splitlines()[-1] == (
        'exec cryoet-pipeline pipeline submit-nextflow -c "${config}" --foreground '
        '--progress-json "${cdpp_dir}/nextflow/progress.json"'
    )
    assert "trap" not in script


@pytest.mark.django_db
def test_script_places_the_reserved_trees(cdpp_plans, cdpp_context):
    reservation = {
        "trees": {
            "miss_alignment": {"run": "run002", "dir": f"{ROOT}/miss_alignment/{SESSION}/run002"},
            "copick": {"run": "run001", "dir": f"{ROOT}/copick/{SESSION}/run001"},
        },
        "pipeline_fingerprint": PLAN["fingerprint"],
    }

    script = CdppProcessor().render_script({**PARAMS, "_reserved_runs": reservation}, cdpp_context)

    assert RESERVED_PLACEHOLDER not in script
    assert f"    --tree miss_alignment={ROOT}/miss_alignment/{SESSION}/run002 \\" in script
    assert f"    --tree copick={ROOT}/copick/{SESSION}/run001 \\" in script
    assert f'mkdir -p "${{cdpp_dir}}/nextflow" {ROOT}/miss_alignment/{SESSION}/run002 {ROOT}/copick/' in script
    assert "    --set isonet2.epochs=50 \\" in script


# Submission records


def _execute(cdpp_step, cdpp_run, user, job_id):
    submitter = MagicMock()
    submitter.run_script.return_value = (f"Submitted batch job {job_id}", "")
    submitter.last_script_path = f"/scripts/{job_id}.sh"
    with (
        patch("workflow.execution.RemoteJobSubmitter", return_value=submitter),
        patch("processes.tasks.start_job_status_syncer") as status_syncer,
        patch.object(CdppProcessor, "_start_syncer_task") as progress_syncer,
    ):
        result = PipelineExecutor().execute_pipe(
            pipe_in_plan=cdpp_step,
            proc_run=cdpp_run,
            user=user,
            parameters=dict(PARAMS),
            auth={"username": "test"},
            cluster_id="czii",
        )
    return result, status_syncer, progress_syncer


def _tree_executions(job_id):
    executions = PipeExecution.objects.filter(job_id=job_id).exclude(proc_run__proc_plan__name="czii-cdpp")
    return {execution.parameters["_cdpp"]["tree"]: execution for execution in executions.select_related("proc_run")}


@pytest.mark.django_db
def test_execute_records_every_tree(fake_cluster, cdpp_step, cdpp_run, test_user, test_msi_session):
    _tree_run("czii-miss-alignment", test_msi_session, "run002", fingerprint=FINGERPRINTS["miss_alignment"])

    result, status_syncer, progress_syncer = _execute(cdpp_step, cdpp_run, test_user, "4242")

    own = PipeExecution.objects.get(id=result["pipe_execution_id"])
    assert own.parameters["_reserved_runs"]["trees"]["miss_alignment"]["reused"] is True
    assert own.parameters["_cdpp"] == {
        "pipeline_fingerprint": PLAN["fingerprint"],
        "preset": "insitu_import",
        "cdpp_run": "run001",
        "fingerprint": PLAN["fingerprint"],
        "dir": CDPP_DIR,
        "trees": {"miss_alignment": "run002", "isonet2": "run001", "copick": "run001"},
    }

    trees = _tree_executions("4242")
    assert set(trees) == {"miss_alignment", "isonet2", "copick"}
    for name, execution in trees.items():
        assert execution.status == "submitted"
        assert execution.script_content == own.script_content
        assert execution.parameters["cluster_id"] == "czii"
        assert execution.parameters["_cdpp"]["fingerprint"] == FINGERPRINTS[name]
        assert execution.parameters["_cdpp"]["cdpp_run"] == "run001"
    # The reused run's execution is restarted in place; its previous job becomes an attempt.
    assert trees["miss_alignment"].proc_run.name == "run002"
    assert [attempt["job_id"] for attempt in trees["miss_alignment"].parameters["_attempts"]] == ["100"]
    assert "_attempts" not in trees["isonet2"].parameters

    status_syncer.assert_called_once_with(job_id="4242", cluster_id="czii")
    progress_syncer.assert_called_once()
    assert progress_syncer.call_args.kwargs["syncer_class_path"] == "workflow.processors.cdpp.syncer.CdppSyncer"


@pytest.mark.django_db
def test_relaunch_resumes_the_same_runs(fake_cluster, cdpp_step, cdpp_run, test_user):
    _execute(cdpp_step, cdpp_run, test_user, "5001")
    first = {name: execution.proc_run.name for name, execution in _tree_executions("5001").items()}

    result, _, _ = _execute(cdpp_step, cdpp_run, test_user, "5002")

    # Unchanged parameters: every tree fingerprint matches, so every tree resumes in its run.
    trees = _tree_executions("5002")
    assert {name: execution.proc_run.name for name, execution in trees.items()} == first
    assert all(execution.parameters["_attempts"][-1]["job_id"] == "5001" for execution in trees.values())
    own = PipeExecution.objects.get(id=result["pipe_execution_id"])
    assert own.proc_run == cdpp_run
    assert own.parameters["_attempts"][-1]["job_id"] == "5001"
    assert ProcRun.objects.exclude(proc_plan__name="czii-cdpp").count() == 3


# Registration


@pytest.mark.django_db
def test_registered_with_its_plan(cdpp_step):
    processor = get_processor("cdpp")

    assert processor.allows_run_reuse
    assert not processor.hidden_from_list
    assert cdpp_step.plan.display_name == "CryoET Data Portal Pipeline"
    assert cdpp_step.pipe.software.storage_dirname == "cdpp"
    assert processor.get_processing_base_path() == f"{ROOT}/cdpp"


@pytest.mark.django_db
def test_plan_runs_knows_cdpp(logged_in_client, cdpp_run):
    response = logged_in_client.get("/workflow/v1/execution/plan_runs/", {"plan_type": "cdpp"})

    assert response.status_code == 200
    (session,) = response.json()["sessions"]
    assert session["next_run_name"] == "run002"


def test_progress_syncer_is_registered():
    from workflow.views.job_api import SYNCER_CLASS_PATH, SYNCER_TYPES

    module_path, cls = SYNCER_CLASS_PATH.format(processor="cdpp", cls=SYNCER_TYPES["cdpp"]).rsplit(".", 1)
    assert getattr(importlib.import_module(module_path), cls).processor_name == "cdpp"


@pytest.mark.django_db
def test_dynamic_options_list_aretomo3_runs(logged_in_client, cdpp_plans, test_msi_session):
    ProcRun.objects.create(name="run003", proc_plan=cdpp_plans["czii-live"], msi_session=test_msi_session)

    response = logged_in_client.get("/workflow/v1/processors/cdpp/options/", {"session_id": SESSION})

    assert response.status_code == 200
    assert [option["value"] for option in response.json()["options"]["aretomo3_runs"]] == ["run003"]
