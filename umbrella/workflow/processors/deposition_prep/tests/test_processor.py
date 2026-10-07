"""Render tests for DepositionPrepProcessor."""

from types import SimpleNamespace

from workflow.processors.deposition_prep.processor import DepositionPrepProcessor

PARAMS = {
    "output_dir": "/staged/dep_1/ds_2",
    "config_yaml": "deposition_id: 1\n",
    "config_path": "/staged/dep_1/ds_2/dataprep_config.yaml",
    "copick_config": "/staged/dep_1/ds_2/copick.json",
    "target_dir": "/staged/dep_1/ds_2",
    "copick_flags": '--picks "VLP:relionrefine/2"',
    "prep_env": "/hpc/projects/group.czii/dataportalenv",
}


def _render(**overrides):
    params = {**PARAMS, **overrides}
    return DepositionPrepProcessor().render_script(params, SimpleNamespace(cluster_id="bruno"))


def test_runs_sync_deposit_and_dry_run_push():
    script = _render()
    assert "cryoetportalprep sync /staged/dep_1/ds_2/dataprep_config.yaml" in script
    assert "copick deposit --config /staged/dep_1/ds_2/copick.json" in script
    assert '--picks "VLP:relionrefine/2"' in script
    assert "cryoetportalprep push /staged/dep_1/ds_2/dataprep_config.yaml --dry-run" in script


def test_session_filter_scopes_sync_to_this_datasets_sessions():
    script = _render(session_names=["24nov10", "24nov11"])
    assert "cryoetportalprep sync /staged/dep_1/ds_2/dataprep_config.yaml -s 24nov10 -s 24nov11" in script


def test_no_session_filter_syncs_the_whole_config():
    # Blank session_names leaves the bare sync (processes every dataset in the config).
    assert "cryoetportalprep sync /staged/dep_1/ds_2/dataprep_config.yaml\n" in _render(session_names=[])


def test_validate_can_be_skipped_for_a_per_dataset_job():
    assert "--dry-run" not in _render(run_validate=False)


def test_prep_never_uploads_or_inits():
    script = _render()
    assert "--force" not in script
    assert "cryoetportalprep init" not in script


def test_copick_deposit_skipped_without_selected_annotations():
    assert "copick deposit" not in _render(copick_flags="")


def test_slurm_directives_and_env_rendered():
    script = _render()
    assert "#SBATCH --partition=cpu" in script
    assert "#SBATCH --time=24:00:00" in script
    assert "#SBATCH --mem=8G" in script
    assert "conda activate /hpc/projects/group.czii/dataportalenv" in script


def test_validate_parameters_requires_output_and_config():
    proc = DepositionPrepProcessor()
    assert proc.validate_parameters(PARAMS) == []
    errors = proc.validate_parameters({})
    assert any("output_dir" in e for e in errors)
    assert any("config_path" in e for e in errors)


def test_fails_fast_without_breaking_conda_activate():
    script = _render()
    assert script.index("conda activate") < script.index("set -euo pipefail")


def test_paths_with_spaces_are_shell_quoted():
    script = _render(output_dir="/staged/my dep")
    assert "cd '/staged/my dep'" in script


def test_copick_flags_require_config_and_target():
    proc = DepositionPrepProcessor()
    errors = proc.validate_parameters({"output_dir": "/o", "config_path": "/c", "copick_flags": '--picks "x"'})
    assert any("copick_config and target_dir" in e for e in errors)


def test_script_writes_config_without_shell_expansion_and_preserves_group_access(tmp_path):
    import stat
    import subprocess

    output_dir = tmp_path / "deposition with spaces"
    config_path = output_dir / "dataprep_config.yaml"
    unwanted = tmp_path / "expanded"
    payload = f'END_CONFIG\n$(touch "{unwanted}")\n`touch "{unwanted}"`\n$HOME'
    script = _render(
        output_dir=str(output_dir),
        config_path=str(config_path),
        config_yaml=payload,
        copick_flags="",
        run_validate=False,
    )
    stubs = 'ml() { :; }; conda() { :; }; cryoetportalprep() { test -r "$2"; };\n'
    result = subprocess.run(["bash"], input=stubs + script, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert config_path.read_text() == payload + "\n"
    assert not unwanted.exists()
    assert stat.S_IMODE(config_path.stat().st_mode) & 0o060 == 0o060
    assert list(output_dir.glob("*.tmp.*")) == []


def test_directory_creation_failure_stops_before_sync(tmp_path):
    import subprocess

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("blocked")
    synced = tmp_path / "sync-ran"
    script = _render(
        output_dir=str(blocked_parent / "deposition"),
        config_path=str(blocked_parent / "deposition/dataprep_config.yaml"),
        copick_flags="",
        run_validate=False,
    )
    stubs = f'ml() {{ :; }}; conda() {{ :; }}; cryoetportalprep() {{ touch "{synced}"; }};\n'
    result = subprocess.run(["bash"], input=stubs + script, text=True, capture_output=True)
    assert result.returncode != 0
    assert not synced.exists()


def test_staging_permission_denied_stops_before_sync(tmp_path):
    import os
    import subprocess

    import pytest

    if os.geteuid() == 0:
        pytest.skip("Root bypasses directory write permissions")
    parent = tmp_path / "restricted"
    parent.mkdir()
    parent.chmod(0o500)
    synced = tmp_path / "sync-ran"
    script = _render(
        output_dir=str(parent / "deposition"),
        config_path=str(parent / "deposition/dataprep_config.yaml"),
        copick_flags="",
        run_validate=False,
    )
    stubs = f'ml() {{ :; }}; conda() {{ :; }}; cryoetportalprep() {{ touch "{synced}"; }};\n'
    try:
        result = subprocess.run(["bash"], input=stubs + script, text=True, capture_output=True)
    finally:
        parent.chmod(0o700)
    assert result.returncode != 0
    assert "Permission denied" in result.stderr
    assert not synced.exists()
