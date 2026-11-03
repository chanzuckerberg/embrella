"""Job-side subset prune: filter staged metrics to the selected positions."""

import csv
import json

import pytest
import yaml

from workflow.processors.deposition_prep.subset_prune import main

FIELDS = ["Tilt_Series", "Bad_Patch_All", "Tilt_Axis"]
# Real metrics files carry the .mrc suffix; the script strips it to match normalized picks.
ROWS = [
    {"Tilt_Series": "Position_1.mrc", "Bad_Patch_All": "0,1", "Tilt_Axis": "-96"},
    {"Tilt_Series": "Position_2.mrc", "Bad_Patch_All": "", "Tilt_Axis": "-96"},
    {"Tilt_Series": "Position_3.mrc", "Bad_Patch_All": "2", "Tilt_Axis": "-96"},
]


def _setup(tmp_path):
    aretomo = tmp_path / "aretomo3"
    aretomo.mkdir()
    with (aretomo / "TiltSeries_Metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ROWS)
    output = tmp_path / "staged"
    output.mkdir()
    config_path = output / "dataprep_config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {"datasets": {"ds": {"dataset_id": 2, "sessions": {"24nov10": {"paths": {"aretomo3": str(aretomo)}}}}}}
        )
    )
    return str(config_path), str(output), output / "2" / "24nov10_TiltSeries_Metrics.csv"


def _read(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


SESSIONS = json.dumps(["24nov10"])


def test_prunes_to_selected_positions_preserving_columns(tmp_path):
    config_path, output, dst = _setup(tmp_path)
    main(config_path, output, "2", SESSIONS, json.dumps({"24nov10": ["Position_1", "Position_3"]}))
    fields, rows = _read(dst)
    assert fields == FIELDS  # filtered copy keeps every column, incl. Bad_Patch_All
    assert [r["Tilt_Series"] for r in rows] == ["Position_1.mrc", "Position_3.mrc"]


def test_empty_subset_clears_stale_copy(tmp_path):
    config_path, output, dst = _setup(tmp_path)
    dst.parent.mkdir(parents=True)
    dst.write_text("stale")
    main(config_path, output, "2", SESSIONS, json.dumps({}))
    assert not dst.exists()


def test_missing_position_fails_loudly(tmp_path):
    config_path, output, _ = _setup(tmp_path)
    with pytest.raises(SystemExit):
        main(config_path, output, "2", SESSIONS, json.dumps({"24nov10": ["Position_9"]}))
