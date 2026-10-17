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
            with tempfile.TemporaryFile(mode="w+b") as output:
                completed = subprocess.run(
                    ["cryoetportalprep", "push", str(scoped), "--dry-run"],
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                output.seek(0, 2)
                size = output.tell()
                output.seek(max(0, size - 32000))
                text = ANSI.sub("", output.read().decode("utf-8", errors="replace"))
            lines = text.splitlines()
            # Indent any echoed line that mimics our marker so the CLI's output can't forge the result.
            print("\n".join(f" {ln}" if ln.startswith(MARKER) else ln for ln in lines))
        # Exit code decides pass/fail; messages are best-effort text matches.
        if completed.returncode == 0:
            result["status"] = "passed"
            result["warnings"] = [{"message": ln[:500]} for ln in lines if re.search(r"\bwarn", ln, re.IGNORECASE)][:20]
        else:
            result["status"] = "failed"
            issues = [
                {"message": ln[:500]}
                for ln in lines
                if ln.lstrip().startswith("- ") or re.search(r"\b(error|failed|exception|invalid)\b", ln, re.IGNORECASE)
            ][:20]
            # A failed result must carry a reason, even when no line matched.
            result["blocking_issues"] = issues or [
                {"message": f"Dry-run validation exited with code {completed.returncode}."}
            ]
    except Exception:
        result["blocking_issues"] = [{"message": "Could not run pre-flight validation. Retry preparation."}]
    print(MARKER + json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    validate(*sys.argv[1:])
