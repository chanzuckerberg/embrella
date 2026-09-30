"""Render tests for DepositionPrepProcessor."""

from types import SimpleNamespace

from workflow.processors.deposition_prep.processor import DepositionPrepProcessor

PARAMS = {
    "output_dir": "/staged/dep_1/ds_2",
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
