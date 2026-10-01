"""Render tests for DepositionPushProcessor."""

from types import SimpleNamespace

from workflow.processors.deposition_push.processor import DepositionPushProcessor

PARAMS = {
    "staged_dir": "/staged/dep_1/ds_2",
    "s3_dest": "s3://cryoetportal-biohub-hpc-globus/CZII/1/2/",
}


def _render(cluster_id="bruno", **overrides):
    params = {**PARAMS, **overrides}
    return DepositionPushProcessor().render_script(params, SimpleNamespace(cluster_id=cluster_id))


def test_syncs_dataset_subtree_to_dest():
    script = _render()
    assert "aws s3 sync /staged/dep_1/ds_2 s3://cryoetportal-biohub-hpc-globus/CZII/1/2/ --follow-symlinks" in script


def test_no_credential_handling_in_script():
    # Auth is ambient (cluster env); the script must not fetch or export keys.
    script = _render()
    assert "aws ssm" not in script
    assert "AWS_SECRET_ACCESS_KEY" not in script
    assert "AWS_SESSION_TOKEN" not in script


def test_prologue_sets_up_cluster_env():
    script = _render()
    assert "conda activate dataportalenv" in script
    assert "ml load awscli" in script


def test_fail_fast_around_conda_prologue():
    script = _render()
    assert script.index("set -e") < script.index("conda activate") < script.index("set -euo pipefail")


def test_setup_commands_are_separate_not_chained():
    # && would exempt the first command from set -e, letting a failed load slip through.
    assert "&&" not in _render()


def test_excludes_local_only_artifacts():
    script = _render()
    for pattern in ("dataprep_config.yaml", "sync_job.sh", "__pycache__/*"):
        assert f"--exclude '{pattern}'" in script


def test_omits_delete_flag():
    # --delete removes bucket objects; re-push deletion is a separate, explicit decision.
    assert "--delete" not in _render()


def test_push_does_not_use_cryoetportalprep():
    assert "cryoetportalprep" not in _render()


def test_slurm_directives_and_qos():
    assert "#SBATCH --partition=cpu" in _render()
    assert "--qos=embrella" in _render(cluster_id="czii")


def test_paths_with_spaces_are_shell_quoted():
    assert "aws s3 sync '/staged/my dep'" in _render(staged_dir="/staged/my dep")


def test_validate_parameters_requires_staged_dir_and_dest():
    proc = DepositionPushProcessor()
    assert proc.validate_parameters(PARAMS) == []
    errors = proc.validate_parameters({})
    assert any("staged_dir" in e for e in errors)
    assert any("s3_dest" in e for e in errors)
