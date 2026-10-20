"""Job-side dataset validation; embedded in the prep script without Django dependencies."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER = "DEPOSITION_VALIDATION="
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def validate(config_path, dataset_id):
    # Default to unavailable; always emit a result marker.
    result = {
        "status": "unavailable",
        "attempt": os.environ.get("SLURM_JOB_ID", "local"),
        "dataset_id": None,
        "warnings": [],
        "blocking_issues": [],
    }
    try:
        import yaml

        result["dataset_id"] = int(dataset_id)
        source = Path(config_path)
        config = yaml.safe_load(source.read_text())
        config["datasets"] = {
            name: block for name, block in config["datasets"].items() if block["dataset_id"] == result["dataset_id"]
        }
        if len(config["datasets"]) != 1:
            raise ValueError("Expected exactly one dataset for validation")
        # Validate only this dataset; the shared config keeps siblings.
        with tempfile.TemporaryDirectory() as directory:
            scoped = Path(directory) / "dataprep_config.yaml"
            scoped.write_text(yaml.safe_dump(config))
            # Preserve mtime so push does not mistake the scoped copy for a post-sync edit.
            source_stat = source.stat()
            os.utime(scoped, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
            with tempfile.TemporaryFile(mode="w+b") as output, tempfile.TemporaryFile(mode="w+b") as errors:
                completed = subprocess.run(
                    ["cryoetportalprep", "push", str(scoped), "--dry-run", "--format", "json"],
                    stdout=output,
                    stderr=errors,
                    check=False,
                )
                errors.seek(0, 2)
                errors.seek(max(0, errors.tell() - 32000))
                text = ANSI.sub("", errors.read().decode("utf-8", errors="replace"))
                print("\n".join(f" {line}" if line.startswith(MARKER) else line for line in text.splitlines()))
                output.seek(0)
                report = json.loads(output.read(2_000_000))
            if not isinstance(report, dict) or not isinstance(report.get("valid"), bool):
                raise ValueError("Invalid CLI validation report")
            issues = report.get("issues")
            if not isinstance(issues, list):
                raise ValueError("Missing CLI validation issues")
            for issue in issues:
                if (
                    not isinstance(issue, dict)
                    or issue.get("severity") not in ("error", "warning")
                    or not isinstance(issue.get("message"), str)
                ):
                    raise ValueError("Invalid CLI validation issue")
                severity = issue["severity"]
                message = issue["message"]
                print(f"{severity}: " + message.replace("\n", "\n "))
                item = {"message": message[:500], "path": str(issue.get("path") or "")[:500]}
                target = result["warnings"] if severity == "warning" else result["blocking_issues"]
                if len(target) < 20:
                    target.append(item)
            passed = completed.returncode == 0 and report["valid"] and not result["blocking_issues"]
            result["status"] = "passed" if passed else "failed"
            if not passed and not result["blocking_issues"]:
                result["blocking_issues"] = [
                    {"message": f"Dry-run validation exited with code {completed.returncode}."}
                ]
    except Exception:
        result["status"] = "unavailable"
        result["warnings"] = []
        result["blocking_issues"] = [{"message": "Could not run pre-flight validation. Retry preparation."}]
    print(MARKER + json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    validate(*sys.argv[1:])
