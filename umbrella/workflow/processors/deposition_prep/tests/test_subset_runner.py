"""Exercise the job-side subset resolver that turns a typed CSV path into positions."""

import stat

import pytest
import yaml

from workflow.processors import deposition_subset as runner


def _config(session):
    return {"datasets": {"dataset_1": {"sessions": {"24nov10": session}}}}


def _write(tmp_path, config):
    path = tmp_path / "dataprep_config.yaml"
    path.write_text(yaml.safe_dump(config))
    return path


def _session(config_path, name="24nov10"):
    return yaml.safe_load(config_path.read_text())["datasets"]["dataset_1"]["sessions"][name]


def test_resolves_path_to_positions(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series,Score\nPosition_1.mrc,0.9\nPosition_2,0.8\n")
    config_path = _write(tmp_path, _config({"subset_csv_path": str(csv)}))

    runner.resolve(str(config_path))

    session = _session(config_path)
    assert session["positions"] == ["Position_1", "Position_2"]
    assert "subset_csv_path" not in session


def test_strips_a_leading_bom(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("﻿Tilt_Series\nPosition_1.mrc\n")
    config_path = _write(tmp_path, _config({"subset_csv_path": str(csv)}))

    runner.resolve(str(config_path))

    assert _session(config_path)["positions"] == ["Position_1"]


def test_resolves_each_session_independently(tmp_path):
    first = tmp_path / "a.csv"
    first.write_text("Tilt_Series\nPosition_1\n")
    second = tmp_path / "b.csv"
    second.write_text("Tilt_Series\nPosition_2\n")
    config = {
        "datasets": {
            "dataset_1": {
                "sessions": {
                    "24nov10": {"subset_csv_path": str(first)},
                    "24nov11": {"positions": ["Position_9"]},
                    "24nov12": {"subset_csv_path": str(second)},
                }
            }
        }
    }
    config_path = _write(tmp_path, config)

    runner.resolve(str(config_path))

    assert _session(config_path, "24nov10")["positions"] == ["Position_1"]
    assert _session(config_path, "24nov11")["positions"] == ["Position_9"]
    assert _session(config_path, "24nov12")["positions"] == ["Position_2"]


def test_leaves_resolved_positions_untouched(tmp_path):
    config = _config({"positions": ["Position_5"]})
    config_path = _write(tmp_path, config)

    runner.resolve(str(config_path))

    assert yaml.safe_load(config_path.read_text()) == config


@pytest.mark.parametrize("session", [{"subset_csv_path": "   "}, {"positions": ["Position_5"]}])
def test_blank_or_absent_path_leaves_the_config_unchanged(tmp_path, session):
    config = _config(session)
    config_path = _write(tmp_path, config)

    runner.resolve(str(config_path))

    assert yaml.safe_load(config_path.read_text()) == config


def test_non_dict_config_is_a_no_op(tmp_path):
    config_path = tmp_path / "dataprep_config.yaml"
    config_path.write_text("END_CONFIG\njust text\n")

    runner.resolve(str(config_path))

    assert config_path.read_text() == "END_CONFIG\njust text\n"


def test_rewrite_is_atomic_and_keeps_group_access(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series\nPosition_1\n")
    config_path = _write(tmp_path, _config({"subset_csv_path": str(csv)}))
    config_path.chmod(0o664)

    runner.resolve(str(config_path))

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o664
    assert not list(tmp_path.glob("*.tmp"))


def test_missing_file_fails_the_job(tmp_path):
    config_path = _write(tmp_path, _config({"subset_csv_path": str(tmp_path / "gone.csv")}))
    with pytest.raises(SystemExit, match="Could not read subset CSV"):
        runner.resolve(str(config_path))


def test_non_utf8_csv_fails_cleanly(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_bytes(b"Tilt_Series\n\xff\xfe\n")
    config_path = _write(tmp_path, _config({"subset_csv_path": str(csv)}))
    with pytest.raises(SystemExit, match="Could not parse subset CSV"):
        runner.resolve(str(config_path))


def test_no_tilt_series_column_names_the_column(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Score\n0.9\n")
    config_path = _write(tmp_path, _config({"subset_csv_path": str(csv)}))
    with pytest.raises(SystemExit, match="Tilt_Series"):
        runner.resolve(str(config_path))
