"""Unit tests for the autofill service parsing/mapping (no SSH, no DB)."""

from depositions.services.autofill import (
    _between,
    _extract_session,
    _short_reason,
    map_session_to_metadata,
)

# A realistic per-session block as cryoetportalprep init writes it.
SESSION_BLOCK = {
    "total_dose": 120.0,
    "tilt_axis_angle": None,
    "paths": {"aretomo3": "/hpc/.../aretomo3/24nov10/run001"},
    "acquisition": {
        "pixel_spacing": 1.54,
        "acceleration_voltage_kv": 300.0,
        "spherical_aberration_constant": 2.7,
        "aretomo_version": "AreTomo3 2.1.0",
        "binned_voxel_ratio": 8,
    },
}

CONFIG_YAML = """
output_dir: /tmp/out
deposition_id: "NEW"
datasets:
  "dataset_1":
    dataset_id: "NEW"
    sessions:
      24nov10:
        total_dose: 120.0
        tilt_axis_angle:
        paths:
          aretomo3: /hpc/aretomo3/24nov10/run001
        acquisition:
          pixel_spacing: 1.54
          acceleration_voltage_kv: 300.0
          spherical_aberration_constant: 2.7
          aretomo_version: "AreTomo3 2.1.0"
          binned_voxel_ratio: 8
"""


class TestMapSessionToMetadata:
    def test_maps_acquisition_and_dose(self):
        mapped = map_session_to_metadata(SESSION_BLOCK)
        assert mapped["tiltseries"] == {
            "pixel_spacing": 1.54,
            "acceleration_voltage": 300.0,
            "spherical_aberration_constant": 2.7,
            "total_flux": 120.0,
            "binning_from_frames": 8,
        }
        # Two flavors (denoised + filtered) mirroring deposition_prep._tomograms.
        # voxel_spacing = round(pixel_spacing * binned_voxel_ratio, 3) — mirrors deposition_prep.
        tomograms = mapped["tomograms"]
        assert [t["flavor"] for t in tomograms] == ["denoised", "filtered"]
        denoised, filtered = tomograms
        assert denoised == {
            "reconstruction_software": "AreTomo3 2.1.0",
            "voxel_spacing": 12.32,
            "flavor": "denoised",
            "processing": "denoised",
            "processing_software": "DenoisET",
            "is_visualization_default": True,
        }
        assert filtered == {
            "reconstruction_software": "AreTomo3 2.1.0",
            "voxel_spacing": 12.32,
            "flavor": "filtered",
            "processing": "filtered",
            "processing_software": "AreTomo3 2.1.0",
            "is_visualization_default": False,
        }

    def test_voxel_spacing_omitted_when_inputs_missing(self):
        block = {"acquisition": {"pixel_spacing": 1.54}}  # no binned_voxel_ratio
        assert all("voxel_spacing" not in t for t in map_session_to_metadata(block)["tomograms"])

    def test_null_fields_are_dropped_not_written(self):
        # tilt_axis_angle is None
        mapped = map_session_to_metadata(SESSION_BLOCK)
        assert "tilt_axis" not in mapped["tiltseries"]

    def test_empty_or_none_session_is_safe(self):
        for out in (map_session_to_metadata(None), map_session_to_metadata({})):
            assert out["tiltseries"] == {}
            assert [t["flavor"] for t in out["tomograms"]] == ["denoised", "filtered"]


class TestExtractSession:
    def test_finds_named_session(self):
        cfg = {"datasets": {"dataset_1": {"sessions": {"24nov10": SESSION_BLOCK}}}}
        assert _extract_session(cfg, "24nov10") is SESSION_BLOCK

    def test_falls_back_to_sole_session_on_name_mismatch(self):
        cfg = {"datasets": {"dataset_1": {"sessions": {"other": SESSION_BLOCK}}}}
        assert _extract_session(cfg, "24nov10") is SESSION_BLOCK

    def test_returns_none_when_ambiguous(self):
        cfg = {"datasets": {"d": {"sessions": {"a": {}, "b": {}}}}}
        assert _extract_session(cfg, "missing") is None

    def test_returns_none_for_junk(self):
        assert _extract_session(None, "x") is None
        assert _extract_session("not a dict", "x") is None
        assert _extract_session({}, "x") is None


class TestBetween:
    def test_pulls_marked_block(self):
        text = "noise\nAUTOFILL_YAML_BEGIN\nline1\nline2\nAUTOFILL_YAML_END\ntrailer"
        assert _between(text, "AUTOFILL_YAML_BEGIN", "AUTOFILL_YAML_END") == "line1\nline2"

    def test_missing_markers_returns_none(self):
        assert _between("just noise", "AUTOFILL_YAML_BEGIN", "AUTOFILL_YAML_END") is None

    def test_yaml_roundtrips_through_between(self):
        import yaml

        text = f"chatter\nAUTOFILL_YAML_BEGIN\n{CONFIG_YAML}\nAUTOFILL_YAML_END"
        block = _between(text, "AUTOFILL_YAML_BEGIN", "AUTOFILL_YAML_END")
        session = _extract_session(yaml.safe_load(block), "24nov10")
        assert session["acquisition"]["pixel_spacing"] == 1.54


class TestShortReason:
    def test_extracts_click_error_line(self):
        err = "INFO reading things\nError: Metrics file not found: /x/TiltSeries_Metrics.csv\n"
        assert _short_reason(err) == "Metrics file not found: /x/TiltSeries_Metrics.csv"

    def test_defaults_when_no_error_line(self):
        assert _short_reason("nothing useful here") == "no_config_emitted"
