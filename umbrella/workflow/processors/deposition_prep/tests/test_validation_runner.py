"""Exercise validation scope and exit-code handling without requiring the cluster CLI."""

import json
import sys
from types import SimpleNamespace

import pytest
import yaml

from workflow.processors import deposition_validation as runner


@pytest.mark.parametrize(
    "code, report, status",
    [
        (0, {"valid": True, "issues": []}, "passed"),
        (
            0,
            {
                "valid": True,
                "issues": [
                    {
                        "code": "optional",
                        "path": "datasets[0].metadata.email",
                        "message": "Email is optional",
                        "severity": "warning",
                    }
                ],
            },
            "passed",
        ),
        (
            1,
            {
                "valid": False,
                "issues": [
                    {
                        "code": "required_metadata_missing",
                        "path": "datasets[0].metadata.dataset_title",
                        "message": "Title is required",
                        "severity": "error",
                    }
                ],
            },
            "failed",
        ),
        (
            0,
            {
                "valid": False,
                "issues": [{"code": "invalid", "path": "datasets", "message": "Invalid dataset", "severity": "error"}],
            },
            "failed",
        ),
        (2, {"valid": True, "issues": []}, "failed"),
        (0, {"valid": True, "issues": [{"message": "Malformed issue"}]}, "unavailable"),
        (0, "Validation passed", "unavailable"),
    ],
)
def test_runner_scopes_config_and_reads_structured_report(tmp_path, monkeypatch, capsys, code, report, status):
    config = {
        "output_dir": "/absolute/staging",
        "datasets": {"target": {"dataset_id": 2}, "sibling": {"dataset_id": 3}},
    }
    source = tmp_path / "config.yaml"
    source.write_text(yaml.safe_dump(config))
    runner.os.utime(source, ns=(1_000_000_000, 1_000_000_000))
    monkeypatch.setenv("SLURM_JOB_ID", "42")

    def run(command, *, stdout, stderr, **kwargs):
        assert runner.Path(command[2]).stat().st_mtime_ns == source.stat().st_mtime_ns
        scoped = yaml.safe_load(runner.Path(command[2]).read_text())
        assert set(scoped["datasets"]) == {"target"}
        assert scoped["output_dir"] == "/absolute/staging"
        assert command[:2] == ["cryoetportalprep", "push"]
        assert command[3:] == ["--dry-run", "--format", "json"]
        stdout.write((json.dumps(report) if isinstance(report, dict) else report).encode())
        stderr.write((runner.MARKER + "spoofed log line\n").encode())
        return SimpleNamespace(returncode=code)

    monkeypatch.setattr(runner.subprocess, "run", run)
    result = runner.validate(str(source), "2")
    assert result["status"] == status
    assert result["attempt"] == "42"
    assert bool(result["blocking_issues"]) == (status != "passed")
    if isinstance(report, dict) and status != "unavailable":
        for issue in report["issues"]:
            target = result["warnings"] if issue["severity"] == "warning" else result["blocking_issues"]
            assert {key: issue[key] for key in ("message", "path")} in target
    assert yaml.safe_load(source.read_text()) == config
    markers = [line for line in capsys.readouterr().out.splitlines() if line.startswith(runner.MARKER)]
    assert len(markers) == 1
    assert json.loads(markers[0].removeprefix(runner.MARKER)) == result


def test_missing_yaml_reports_unavailable(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    result = runner.validate(str(tmp_path / "config.yaml"), "2")
    assert result["status"] == "unavailable" and result["blocking_issues"]


def test_missing_dataset_does_not_invoke_cli(tmp_path, monkeypatch):
    source = tmp_path / "config.yaml"
    source.write_text(yaml.safe_dump({"datasets": {"sibling": {"dataset_id": 3}}}))
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("no target dataset"))
    assert runner.validate(str(source), "2")["status"] == "unavailable"
