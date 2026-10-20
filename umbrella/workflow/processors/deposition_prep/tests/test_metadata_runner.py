"""Verify metadata passthrough using a rendered job and a CLI contract stub."""

from pathlib import Path

import yaml


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
        import json
        from pathlib import Path
        import yaml

        config = yaml.safe_load(Path(sys.argv[2]).read_text())
        target = Path(config["output_dir"]) / "2" / "portal_dataset_config.yaml"
        if sys.argv[1] == "sync":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump({"datasets": [{"metadata": config["datasets"]["ds"]["metadata"]}]}))
        elif sys.argv[1] == "push":
            print(json.dumps({"valid": True, "issues": []}))
        else:
            sys.exit(2)
    """)
    )
    executable.chmod(0o755)
    output = tmp_path / "staged"
    metadata = {
        "dataset_title": "Saved title",
        "dataset_description": "Saved description",
        "authors": [{"name": "Ada Lovelace"}],
    }
    config = {"output_dir": str(output), "datasets": {"ds": {"dataset_id": 2, "metadata": metadata, "sessions": {}}}}
    script = DepositionPrepProcessor().render_script(
        {
            "output_dir": str(output),
            "config_path": str(output / "dataprep_config.yaml"),
            "config_yaml": yaml.safe_dump(config),
            "dataset_id": 2,
            "prep_env": "/test/env",
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
    portal = yaml.safe_load((output / "2" / "portal_dataset_config.yaml").read_text())
    assert portal["datasets"][0]["metadata"] == metadata
    validation = next(
        line.removeprefix("DEPOSITION_VALIDATION=")
        for line in result.stdout.splitlines()
        if line.startswith("DEPOSITION_VALIDATION=")
    )
    assert json.loads(validation)["status"] == "passed", result.stdout
