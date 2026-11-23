"""Exercise the job-side subset resolver that turns a typed CSV path into positions."""

import os
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


def _cluster_subset(csv, aretomo_dir, metrics="Tilt_Series\nPosition_1.mrc\nPosition_2\n"):
    aretomo_dir.mkdir()
    if metrics is not None:
        (aretomo_dir / "TiltSeries_Metrics.csv").write_text(metrics)
    return {"subset_csv_path": str(csv), "paths": {"aretomo3": str(aretomo_dir)}}


def test_resolves_path_to_positions(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series,Score\nPosition_1.mrc,0.9\nPosition_2,0.8\n")
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))

    runner.resolve(str(config_path))

    session = _session(config_path)
    assert session["positions"] == ["Position_1", "Position_2"]
    assert "subset_csv_path" not in session


def test_strips_a_leading_bom(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("\ufeffTilt_Series\nPosition_1.mrc\n", encoding="utf-8")
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))

    runner.resolve(str(config_path))

    assert _session(config_path)["positions"] == ["Position_1"]


@pytest.mark.parametrize("newline", [b"\r", b"\r\n"], ids=["CR", "CRLF"])
def test_resolves_csv_with_carriage_returns(tmp_path, newline):
    csv = tmp_path / "subset.csv"
    csv.write_bytes(newline.join([b"Tilt_Series", b"Position_1.mrc", b"Position_2", b""]))
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))

    runner.resolve(str(config_path))

    assert _session(config_path)["positions"] == ["Position_1", "Position_2"]


def test_resolves_each_session_independently(tmp_path):
    first = tmp_path / "a.csv"
    first.write_text("Tilt_Series\nPosition_1\n")
    second = tmp_path / "b.csv"
    second.write_text("Tilt_Series\nPosition_2\n")
    config = {
        "datasets": {
            "dataset_1": {
                "sessions": {
                    "24nov10": _cluster_subset(first, tmp_path / "aretomo10", "Tilt_Series\nPosition_1\n"),
                    "24nov11": {"positions": ["Position_9"]},
                    "24nov12": _cluster_subset(second, tmp_path / "aretomo12", "Tilt_Series\nPosition_2.mrc\n"),
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
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))
    config_path.chmod(0o664)

    runner.resolve(str(config_path))

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o664
    assert not list(tmp_path.glob("*.tmp"))


def test_missing_file_fails_the_job(tmp_path):
    config_path = _write(tmp_path, _config(_cluster_subset(tmp_path / "gone.csv", tmp_path / "aretomo")))
    with pytest.raises(SystemExit, match="Could not read subset CSV"):
        runner.resolve(str(config_path))


def test_rejects_a_non_regular_file(tmp_path):
    fifo = tmp_path / "subset.csv"
    os.mkfifo(fifo)  # a FIFO (or symlink to /dev/zero) could block or never end
    config_path = _write(tmp_path, _config(_cluster_subset(fifo, tmp_path / "aretomo")))
    with pytest.raises(SystemExit, match="is not a regular file"):
        runner.resolve(str(config_path))


def test_rejects_an_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "MAX_CSV_BYTES", 64)
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series\n" + "Position_1\n" * 10)
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))
    with pytest.raises(SystemExit, match="exceeds the"):
        runner.resolve(str(config_path))


def test_non_utf8_csv_fails_cleanly(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_bytes(b"Tilt_Series\n\xff\xfe\n")
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))
    with pytest.raises(SystemExit, match="Could not parse subset CSV"):
        runner.resolve(str(config_path))


def test_no_tilt_series_column_names_the_column(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Score\n0.9\n")
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))
    with pytest.raises(SystemExit, match="Tilt_Series"):
        runner.resolve(str(config_path))


def test_only_stages_matching_positions_and_warns_without_naming_skipped_entries(tmp_path, capsys):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series\nPosition_2.mrc\nOther_Position\nPosition_1\nPosition_2\nOther_Position.mrc\n")
    config_path = _write(tmp_path, _config(_cluster_subset(csv, tmp_path / "aretomo")))

    runner.resolve(str(config_path))

    assert _session(config_path)["positions"] == ["Position_2", "Position_1"]
    stderr = capsys.readouterr().err
    assert "skipped 1 of 3 requested positions" in stderr
    assert "Other_Position" not in stderr


def test_no_overlap_fails_without_rewriting_config(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series\nOther_Position.mrc\n")
    config = _config(_cluster_subset(csv, tmp_path / "aretomo"))
    config_path = _write(tmp_path, config)

    with pytest.raises(SystemExit, match="none of the positions.*match this session's tilt series"):
        runner.resolve(str(config_path))

    assert yaml.safe_load(config_path.read_text()) == config


def test_missing_session_metrics_fails_without_rewriting_config(tmp_path):
    csv = tmp_path / "subset.csv"
    csv.write_text("Tilt_Series\nPosition_1\n")
    config = _config(_cluster_subset(csv, tmp_path / "aretomo", metrics=None))
    config_path = _write(tmp_path, config)

    with pytest.raises(SystemExit, match="Could not read tilt series metrics for session 24nov10"):
        runner.resolve(str(config_path))

    assert yaml.safe_load(config_path.read_text()) == config
