"""Render tests for DepositionPushProcessor."""

from types import SimpleNamespace

import pytest

from workflow.processors.deposition_push.processor import DepositionPushProcessor

PARAMS = {
    "staged_dir": "/staged/dep_1/ds_2",
    "s3_dest": "s3://cryoetportal-biohub-hpc-globus/CZII/10001/20002/",
}


def _render(cluster_id="bruno", **overrides):
    params = {**PARAMS, **overrides}
    return DepositionPushProcessor().render_script(params, SimpleNamespace(cluster_id=cluster_id))


def test_syncs_dataset_subtree_to_dest():
    script = _render()
    assert "s3_dest=s3://cryoetportal-biohub-hpc-globus/CZII/10001/20002/" in script
    assert 'aws s3 sync /staged/dep_1/ds_2 "$s3_dest" --delete --follow-symlinks' in script


def test_writes_ingest_ready_marker_after_successful_sync():
    script = _render()
    marker = 'aws s3 cp - "${s3_dest%/}/ingest.ready"'
    assert marker in script
    assert script.index('if [ "$upload_status" -ne 0 ]') < script.index(marker)


@pytest.mark.parametrize(
    "destination,allowed",
    [
        ("s3://another-bucket/institution.v1/10001/20002", True),
        ("s3://example-bucket/", False),
        ("s3://example-bucket/CZII/10001/", False),
        ("s3://example-bucket/CZII/10001/1234/", False),
        ("s3://example-bucket/CZII/10001/123456/", False),
        ("s3://example-bucket/CZII/../10001/20002/", False),
    ],
)
def test_job_checks_destination_before_invoking_aws(tmp_path, destination, allowed):
    import os
    import subprocess

    script = _render(s3_dest=destination, prologue=":")
    result = subprocess.run(
        ["bash"],
        input='python() { :; }; aws() { echo "AWS_INVOKED:$4"; echo "AWS_ARGS:$*"; };\n' + script,
        env={**os.environ, "SLURM_SUBMIT_DIR": str(tmp_path)},
        text=True,
        capture_output=True,
        timeout=10,
    )
    if allowed:
        assert result.returncode == 0, result.stderr
        assert f"AWS_INVOKED:{destination}" in result.stdout
        assert " --delete --follow-symlinks" in result.stdout
    else:
        assert result.returncode != 0
        assert "Invalid upload destination" in result.stderr
        assert "AWS_INVOKED" not in result.stdout


def test_no_credential_handling_in_script():
    # Auth is ambient (cluster env); the script must not fetch or export keys.
    script = _render()
    assert "aws ssm" not in script
    assert "AWS_SECRET_ACCESS_KEY" not in script
    assert "AWS_SESSION_TOKEN" not in script


def test_exports_quoted_aws_profile_before_upload(settings):
    settings.DEPOSITION_AWS_PROFILE = "institution upload; $(touch unexpected)"
    script = _render(prologue="ml load awscli")
    assert (
        script.index("ml load awscli")
        < script.index("export AWS_PROFILE='institution upload; $(touch unexpected)'")
        < script.index("aws s3 sync")
    )


def test_no_aws_profile_export_when_unset(settings):
    settings.DEPOSITION_AWS_PROFILE = ""
    assert "export AWS_PROFILE=" not in _render()


def test_prologue_sets_up_cluster_env():
    script = _render()
    assert "ml load anaconda" in script
    assert "ml load awscli" in script
    assert "conda activate" not in script


def test_fail_fast_around_module_prologue():
    script = _render()
    assert script.index("set -e") < script.index("ml load anaconda") < script.index("set -euo pipefail")


def test_setup_commands_are_separate_not_chained():
    # && would exempt the first command from set -e, letting a failed load slip through.
    assert "&&" not in _render()


def test_excludes_local_only_artifacts():
    script = _render()
    for pattern in ("dataprep_config.yaml", "sync_job.sh", "__pycache__/*"):
        assert f"--exclude '{pattern}'" in script


def test_push_does_not_use_cryoetportalprep():
    assert "cryoetportalprep" not in _render()


def test_slurm_directives_and_qos():
    assert "#SBATCH --partition=cpu" in _render()
    assert "--qos=embrella" in _render(cluster_id="czii")


def test_requests_slurm_notifications_for_the_submission_owner_when_provided():
    script = _render()
    assert "#SBATCH --mail-type=END,FAIL" in script
    assert "--mail-user" not in script
    assert "#SBATCH --mail-user=owner@example.org" in _render(slurm_mail_user="owner@example.org")


def test_paths_with_spaces_are_shell_quoted():
    assert "aws s3 sync '/staged/my dep'" in _render(staged_dir="/staged/my dep")


def test_validate_parameters_requires_staged_dir_and_dest():
    proc = DepositionPushProcessor()
    assert proc.validate_parameters(PARAMS) == []
    errors = proc.validate_parameters({})
    assert any("staged_dir" in e for e in errors)
    assert any("s3_dest" in e for e in errors)
