"""Render tests for DepositionPushProcessor."""

from types import SimpleNamespace

from workflow.processors.deposition_push.processor import DepositionPushProcessor

PARAMS = {
    "staged_dir": "/staged/dep_1/ds_2",
    "s3_dest": "s3://cryoetportal-biohub-hpc-globus/CZII/1/2/",
    "aws_cli_path": "/hpc/apps/awscli/v2/2.27.43/dist",
    "aws_key_param": "/env/AWS_ACCESS_KEY_NAME",
    "aws_secret_param": "/env/AWS_SECRET_ACCESS_KEY",
}


def _render(cluster_id="bruno", **overrides):
    params = {**PARAMS, **overrides}
    return DepositionPushProcessor().render_script(params, SimpleNamespace(cluster_id=cluster_id))


def test_runs_aws_s3_sync_to_dest():
    script = _render()
    assert "aws s3 sync --follow-symlinks /staged/dep_1/ds_2 s3://cryoetportal-biohub-hpc-globus/CZII/1/2/" in script


def test_fetches_both_creds_before_exporting():
    script = _render()
    assert script.count("aws ssm get-parameters") == 2
    assert script.index("aws_secret=") < script.index("export AWS_ACCESS_KEY_ID=")
    assert 'export AWS_ACCESS_KEY_ID="$aws_key"' in script
    assert 'export AWS_SECRET_ACCESS_KEY="$aws_secret"' in script


def test_clears_inherited_session_token():
    assert "unset AWS_SESSION_TOKEN" in _render()


def test_aborts_when_credentials_missing():
    script = _render()
    assert "Failed to read AWS credentials from SSM" in script
    assert "exit 1" in script


def test_no_staging_credentials_baked_in():
    assert "cryoet-staging-happy" not in _render()


def test_push_does_not_use_cryoetportalprep():
    assert "cryoetportalprep" not in _render()


def test_slurm_time_is_long_and_directives_render():
    script = _render()
    assert "#SBATCH --time=72:00:00" in script
    assert "#SBATCH --partition=cpu" in script


def test_czii_gets_qos():
    assert "--qos=embrella" in _render(cluster_id="czii")


def test_paths_with_spaces_are_shell_quoted():
    assert "aws s3 sync --follow-symlinks '/staged/my dep'" in _render(staged_dir="/staged/my dep")


def test_fails_fast():
    assert "set -euo pipefail" in _render()


def test_validate_parameters_requires_all_inputs():
    proc = DepositionPushProcessor()
    assert proc.validate_parameters(PARAMS) == []
    errors = proc.validate_parameters({"staged_dir": "/s", "s3_dest": "s3://b/"})
    assert any("aws_cli_path" in e for e in errors)
    assert any("aws_key_param" in e for e in errors)
    assert any("aws_secret_param" in e for e in errors)
