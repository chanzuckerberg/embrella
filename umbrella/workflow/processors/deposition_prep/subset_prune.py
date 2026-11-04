"""Job-side: before ``cryoetportalprep sync``, prune each session's staged
TiltSeries_Metrics.csv to the custom subset. Writes to``<output_dir>/<dataset_id>/<session>_TiltSeries_Metrics.csv``
"""

import csv
import json
import sys
from pathlib import Path

import yaml

METRICS = "TiltSeries_Metrics.csv"


def _position(value) -> str:
    return str(value or "").strip().removesuffix(".mrc")


def main(config_path, output_dir, dataset_id, session_names_json, subset_json):
    session_names = json.loads(session_names_json)
    subset = json.loads(subset_json)
    out = Path(output_dir)
    subdir = out / str(dataset_id)

    # Clear stale pruned copies (both locations) so switching back to all-mode or
    # changing the selection starts clean and the CLI recopies the full metrics.
    for name in session_names:
        for stale in (subdir / f"{name}_{METRICS}", out / f"{name}_{METRICS}"):
            stale.unlink(missing_ok=True)
    if not subset:
        return

    config = yaml.safe_load(Path(config_path).read_text())
    block = next(b for b in config["datasets"].values() if str(b.get("dataset_id")) == str(dataset_id))
    subdir.mkdir(parents=True, exist_ok=True)
    for name, positions in subset.items():
        keep = set(positions)  # already normalized in submit; only the CSV side needs _position
        src = Path(block["sessions"][name]["paths"]["aretomo3"]) / METRICS
        with src.open(newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            rows = [r for r in reader if _position(r.get("Tilt_Series")) in keep]
        missing = sorted(keep - {_position(r.get("Tilt_Series")) for r in rows})
        if missing:
            sys.exit(f"subset: selected positions not found in {src}: {', '.join(missing)}")
        dst = subdir / f"{name}_{METRICS}"
        with dst.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"subset: {name} kept {len(rows)} selected positions -> {dataset_id}/{dst.name}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
