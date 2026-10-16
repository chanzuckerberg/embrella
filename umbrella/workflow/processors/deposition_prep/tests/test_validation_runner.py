"""Exercise validation scope and exit-code handling without requiring the cluster CLI."""

import sys
from types import SimpleNamespace

import pytest
import yaml

from workflow.processors import deposition_validation as runner


@pytest.mark.parametrize(
    "code, output, status, message",
    [
        (0, "WARNING: optional metadata\n", "passed", "optional metadata"),
        (1, "ERROR: missing tomogram\n", "failed", "missing tomogram"),
        (2, "unexpected output\n", "failed", "Dry-run validation exited with code 2."),
        (
            1,
            "Validation FAILED:\n  - [dataset] datasets[0]: no authors listed\nError: 1 validation error(s).\n",
            "failed",
            "no authors listed",
        ),
        # 40 KB of multi-byte chars: the 32 KB tail cut can split a char, so decode must not crash.
        (0, "é" * 20000 + "x", "passed", None),
    ],
)
def test_runner_scopes_config_and_uses_exit_code(tmp_path, monkeypatch, capsys, code, output, status, message):
    config = {
        "output_dir": "/absolute/staging",
        "datasets": {"target": {"dataset_id": 2}, "sibling": {"dataset_id": 3}},
    }
    source = tmp_path / "config.yaml"
    source.write_text(yaml.safe_dump(config))
    runner.os.utime(source, ns=(1_000_000_000, 1_000_000_000))
    monkeypatch.setenv("SLURM_JOB_ID", "42")

    def run(command, *, stdout, **kwargs):
        assert runner.Path(command[2]).stat().st_mtime_ns == source.stat().st_mtime_ns
        scoped = yaml.safe_load(runner.Path(command[2]).read_text())
        assert set(scoped["datasets"]) == {"target"}
        assert scoped["output_dir"] == "/absolute/staging"
        assert command[:2] == ["cryoetportalprep", "push"] and command[-1] == "--dry-run"
        stdout.write(output.encode("utf-8"))
        return SimpleNamespace(returncode=code)

    monkeypatch.setattr(runner.subprocess, "run", run)
    result = runner.validate(str(source), "2")
    assert result["status"] == status
    assert result["attempt"] == "42"
    assert bool(result["blocking_issues"]) == (status == "failed")
    if message is not None:
        assert any(message in item["message"] for item in result["warnings"] + result["blocking_issues"])
    assert yaml.safe_load(source.read_text()) == config  # sibling config untouched
    assert runner.MARKER in capsys.readouterr().out


def test_missing_yaml_reports_unavailable(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    result = runner.validate(str(tmp_path / "config.yaml"), "2")
    assert result["status"] == "unavailable" and result["blocking_issues"]


def test_missing_dataset_does_not_invoke_cli(tmp_path, monkeypatch):
    source = tmp_path / "config.yaml"
    source.write_text(yaml.safe_dump({"datasets": {"sibling": {"dataset_id": 3}}}))
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("no target dataset"))
    assert runner.validate(str(source), "2")["status"] == "unavailable"
