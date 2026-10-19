"""Verify metadata delivery without SSH or an installed preparation CLI."""

import copy
import stat
from pathlib import Path

import pytest
import yaml

from workflow.processors.deposition_metadata import apply_metadata


def test_replaces_template_fields_and_preserves_generated_sections(tmp_path):
    path = tmp_path / "portal_dataset_config.yaml"
    generated = {
        "datasets": [
            {
                "metadata": {
                    "dataset_identifier": 2,
                    "dataset_title": "TODO_DATASET_TITLE",
                    "authors": [{"name": "TODO_AUTHOR_NAME", "email": "TODO_EMAIL"}],
                    "funding": [{"grant_id": "TODO_GRANT_ID"}],
                    "tissue": {"id": "TODO_TISSUE_ID"},
                    "dates": {"release_date": "2026-10-19"},
                },
                "sources": [{"literal": {"value": ["2"]}}],
            }
        ],
        "tomograms": [{"sources": [{"source_glob": {"list_glob": "{run_name}_Vol.mrc"}}]}],
        "annotations": [{"metadata": {"annotation_method": "Reviewed method"}}],
        "standardization_config": {"source_prefix": "1/2"},
    }
    path.write_text(yaml.safe_dump(generated))
    path.chmod(0o660)
    patch = {
        "dataset_identifier": 2,
        "dataset_title": "Reviewed dataset",
        "dataset_description": "Saved wizard description",
        "authors": [{"name": "Ada Lovelace"}],
        "funding": None,
        "tissue": None,
    }
    apply_metadata(path, patch)
    result = yaml.safe_load(path.read_text())
    expected = copy.deepcopy(generated)
    expected["datasets"][0]["metadata"].update(patch)
    del expected["datasets"][0]["metadata"]["funding"]
    del expected["datasets"][0]["metadata"]["tissue"]
    assert result == expected
    assert stat.S_IMODE(path.stat().st_mode) == 0o660
    assert "TODO_" not in path.read_text()
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("datasets", [[], [{"metadata": {"dataset_identifier": 3}}], [{}, {}]])
def test_wrong_or_missing_target_does_not_overwrite_portal_yaml(tmp_path, datasets):
    path = tmp_path / "portal_dataset_config.yaml"
    original = yaml.safe_dump({"datasets": datasets})
    path.write_text(original)
    with pytest.raises(ValueError):
        apply_metadata(path, {"dataset_identifier": 2, "dataset_title": "Reviewed"})
    assert path.read_text() == original


def test_rendered_prep_validates_the_reviewed_metadata(tmp_path):
    import json
    import os
    import subprocess
    import sys
    import textwrap
    from types import SimpleNamespace

    from workflow.processors.deposition_prep.processor import DepositionPrepProcessor

    executable = tmp_path / "cryoetportalprep"
    executable.write_text(
        f"#!{sys.executable}\n"
        + textwrap.dedent("""
        import sys
        from pathlib import Path
        import yaml

        config = yaml.safe_load(Path(sys.argv[2]).read_text())
        target = Path(config["output_dir"]) / "2" / "portal_dataset_config.yaml"
        if sys.argv[1] == "sync":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump({
                "datasets": [{"metadata": {"dataset_identifier": 2,
                    "dataset_title": "TODO_DATASET_TITLE",
                    "authors": [{"name": "TODO_AUTHOR_NAME", "email": "TODO_EMAIL"}],
                    "funding": [{"grant_id": "TODO_GRANT_ID"}]},
                    "sources": [{"literal": {"value": ["2"]}}]}],
                "tomograms": [{"sources": [{"source_glob": {"list_glob": "{run_name}_Vol.mrc"}}]}],
            }))
        elif sys.argv[1] == "push":
            assert sys.argv[-1] == "--dry-run"
            document = yaml.safe_load(target.read_text())
            metadata = document["datasets"][0]["metadata"]
            assert metadata["dataset_title"] == "Saved title"
            assert metadata["dataset_description"] == "Saved description"
            assert metadata["authors"] == [{"name": "Ada Lovelace"}]
            assert "funding" not in metadata
            assert document["datasets"][0]["sources"] == [{"literal": {"value": ["2"]}}]
            assert document["tomograms"][0]["sources"][0]["source_glob"]["list_glob"] == "{run_name}_Vol.mrc"
            assert "TODO_" not in target.read_text()
            print("Validation passed.")
        else:
            sys.exit(2)
    """)
    )
    executable.chmod(0o755)
    output = tmp_path / "staged"
    config = {"output_dir": str(output), "datasets": {"ds": {"dataset_id": 2, "sessions": {}}}}
    script = DepositionPrepProcessor().render_script(
        {
            "output_dir": str(output),
            "config_path": str(output / "dataprep_config.yaml"),
            "config_yaml": yaml.safe_dump(config),
            "dataset_id": 2,
            "prep_env": "/test/env",
            "portal_metadata": {
                "dataset_identifier": 2,
                "dataset_title": "Saved title",
                "dataset_description": "Saved description",
                "authors": [{"name": "Ada Lovelace"}],
                "funding": None,
            },
        },
        SimpleNamespace(cluster_id="test"),
    )
    result = subprocess.run(
        ["bash"],
        input="ml() { :; }; conda() { :; };\n" + script,
        text=True,
        capture_output=True,
        timeout=20,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{Path(sys.executable).parent}:{os.environ['PATH']}",
            "SLURM_SUBMIT_DIR": str(tmp_path),
            "SLURM_JOB_ID": "42",
        },
    )
    assert result.returncode == 0, result.stderr
    validation = next(
        line.removeprefix("DEPOSITION_VALIDATION=")
        for line in result.stdout.splitlines()
        if line.startswith("DEPOSITION_VALIDATION=")
    )
    assert json.loads(validation)["status"] == "passed", result.stdout
