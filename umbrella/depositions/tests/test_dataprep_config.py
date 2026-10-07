"""Deployment-config generation uses saved data without init, SSH, or SLURM."""

from copy import deepcopy

import pytest
import yaml
from stores.models import PathType
from tem.models import MsiSession

from depositions.models import Dataset, Deposition, DepositionSession, TiltseriesMetadata, TomogramMetadata
from depositions.services.dataprep_config import (
    build_dataprep_config,
    dataprep_config_yaml,
)
from depositions.services.exceptions import SubmissionValidationError

RAW_SESSION = {
    "paths": {
        "aretomo3": "/hpc/aretomo3/24nov10/run001",
        "mdoc": "/hpc/mdoc/24nov10",
        "frames": "/hpc/frames/24nov10",
        "gain": "/hpc/gains/reference.gain",
        "denoise": "/hpc/denoiset/24nov10/run002",
    },
    "acquisition": {
        "pixel_spacing": 1.54,
        "acceleration_voltage_kv": 300,
        "spherical_aberration_constant": 2.7,
        "aretomo_version": "AreTomo3 2.1.0",
        "binned_voxel_ratio": 8,
    },
    "total_dose": 120,
    "tilt_axis_angle": 85,
}


@pytest.fixture
def dataset(db, test_msi_session):
    deposition = Deposition.objects.create(title="Dep", deposition_id=101)
    dataset = Dataset.objects.create(deposition=deposition, title="Dataset", dataset_id=202)
    session = DepositionSession.objects.create(
        dataset=dataset, msi_session=test_msi_session, aretomo_run_name="run001", denoise_run_name="run002"
    )
    TiltseriesMetadata.objects.create(
        session=session,
        autofill_metadata=deepcopy(RAW_SESSION),
        pixel_spacing=1.54,
        acceleration_voltage=300,
        spherical_aberration_constant=2.7,
        total_flux=120,
        tilt_axis=85,
    )
    return dataset


def _build(dataset, **kwargs):
    return build_dataprep_config(dataset.deposition, output_dir="/staging/101", **kwargs)


def _session(config, name="24nov10"):
    return config["datasets"]["dataset_202"]["sessions"][name]


def test_builds_deployment_config_with_reserved_ids(dataset):
    config = _build(dataset)
    assert config["output_dir"] == "/staging/101"
    assert config["deposition_id"] == 101
    assert config["sync_destination"] == "s3://cryoetportal-biohub-hpc-globus/CZII"
    assert config["datasets"]["dataset_202"]["dataset_id"] == 202
    assert _session(config) == RAW_SESSION


def test_includes_every_dataset_in_the_deposition(dataset, test_session_plan):
    other = Dataset.objects.create(deposition=dataset.deposition, title="Dataset 2", dataset_id=303)
    session = DepositionSession.objects.create(
        dataset=other,
        msi_session=MsiSession.objects.create(name="24dec01", session_plan=test_session_plan),
        aretomo_run_name="run009",
    )
    TiltseriesMetadata.objects.create(session=session, autofill_metadata=deepcopy(RAW_SESSION), pixel_spacing=1.54)
    config = _build(dataset)
    assert set(config["datasets"]) == {"dataset_202", "dataset_303"}
    assert config["datasets"]["dataset_303"]["dataset_id"] == 303


def test_user_edits_override_autofill_without_changing_saved_raw_data(dataset):
    metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
    metadata.pixel_spacing = 2.0
    metadata.acceleration_voltage = 200
    metadata.spherical_aberration_constant = 2.0
    metadata.total_flux = 90
    metadata.tilt_axis = 0
    metadata.save()

    config = _session(_build(dataset))
    assert config["acquisition"] == {
        **RAW_SESSION["acquisition"],
        "pixel_spacing": 2.0,
        "acceleration_voltage_kv": 200,
        "spherical_aberration_constant": 2.0,
    }
    assert config["total_dose"] == 90
    assert config["tilt_axis_angle"] == 0
    assert config["paths"] == RAW_SESSION["paths"]
    metadata.refresh_from_db()
    assert metadata.autofill_metadata == RAW_SESSION


def test_cleared_fields_do_not_restore_old_autofill_values(dataset):
    TiltseriesMetadata.objects.filter(session__dataset=dataset).update(tilt_axis=None, total_flux=None)
    config = _session(_build(dataset))
    assert config["tilt_axis_angle"] is None
    assert config["total_dose"] is None


def test_edited_filtered_tomogram_updates_acquisition(dataset):
    session = dataset.sessions.get()
    TomogramMetadata.objects.create(
        session=session, flavor="filtered", voxel_spacing=15.4, reconstruction_software="AreTomo3 reviewed"
    )
    acquisition = _session(_build(dataset))["acquisition"]
    assert acquisition["aretomo_version"] == "AreTomo3 reviewed"
    assert acquisition["binned_voxel_ratio"] == pytest.approx(10)
    assert acquisition["pixel_spacing"] == 1.54


def test_cleared_tomogram_fields_do_not_restore_autofill(dataset):
    TomogramMetadata.objects.create(session=dataset.sessions.get(), flavor="filtered")
    acquisition = _session(_build(dataset))["acquisition"]
    assert acquisition["aretomo_version"] == ""
    assert acquisition["binned_voxel_ratio"] is None


@pytest.mark.parametrize("pixel_spacing", [None, 0, -1])
def test_rejects_invalid_spacing_when_deriving_voxel_ratio(dataset, pixel_spacing):
    session = dataset.sessions.get()
    TiltseriesMetadata.objects.filter(session=session).update(pixel_spacing=pixel_spacing)
    TomogramMetadata.objects.create(session=session, flavor="filtered", voxel_spacing=12.32)
    with pytest.raises(SubmissionValidationError, match="positive pixel and voxel spacing"):
        _build(dataset)


def test_assembles_all_sessions_and_round_trips_yaml(dataset, test_session_plan):
    second = DepositionSession.objects.create(
        dataset=dataset,
        msi_session=MsiSession.objects.create(name="24nov11", session_plan=test_session_plan),
        aretomo_run_name="run003",
    )
    raw = deepcopy(RAW_SESSION)
    raw["paths"]["aretomo3"] = "/hpc/aretomo3/24nov11/run003"
    TiltseriesMetadata.objects.create(session=second, autofill_metadata=raw, pixel_spacing=2)
    text = dataprep_config_yaml(
        dataset.deposition, output_dir="/staging/101", sync_destination="s3://test-bucket/review"
    )
    parsed = yaml.safe_load(text)
    assert list(parsed["datasets"]["dataset_202"]["sessions"]) == ["24nov10", "24nov11"]
    assert _session(parsed, "24nov11")["paths"]["aretomo3"] == raw["paths"]["aretomo3"]
    assert _session(parsed, "24nov11")["acquisition"]["pixel_spacing"] == 2
    assert parsed["sync_destination"] == "s3://test-bucket/review"
    assert "metadata:" not in text  # The portal metadata YAML is a different artifact.


@pytest.mark.parametrize("missing_id", ["deposition", "dataset"])
def test_rejects_missing_reservations(dataset, missing_id):
    if missing_id == "deposition":
        dataset.deposition.deposition_id = None  # checked on the passed deposition object
    else:
        Dataset.objects.filter(pk=dataset.pk).update(dataset_id=None)  # datasets are read from the db
    with pytest.raises(SubmissionValidationError, match="Reserve"):
        build_dataprep_config(dataset.deposition, output_dir="/staging/101")


def test_rejects_when_no_dataset_is_ready(dataset):
    dataset.sessions.all().delete()
    with pytest.raises(SubmissionValidationError, match="ready to prepare"):
        _build(dataset)


def test_skips_a_not_ready_dataset(dataset):
    # A draft dataset (no sessions yet) must not block the ready one.
    Dataset.objects.create(deposition=dataset.deposition, title="Draft", dataset_id=404)
    config = _build(dataset)
    assert set(config["datasets"]) == {"dataset_202"}


@pytest.mark.parametrize("raw", [{}, "invalid", []])
def test_skips_dataset_never_autofilled(dataset, raw):
    # Empty/missing autofill = a draft that never ran auto-fill - skipped.
    metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
    metadata.autofill_metadata = raw
    metadata.save()
    with pytest.raises(SubmissionValidationError, match="ready to prepare"):
        _build(dataset)


def test_skips_dataset_without_autofill_metadata(dataset):
    TiltseriesMetadata.objects.filter(session__dataset=dataset).delete()
    with pytest.raises(SubmissionValidationError, match="ready to prepare"):
        _build(dataset)


@pytest.mark.parametrize("raw", [{"paths": {}}, {"paths": {"aretomo3": "/a"}}])
def test_rejects_malformed_saved_autofill(dataset, raw):
    metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
    metadata.autofill_metadata = raw
    metadata.save()
    with pytest.raises(SubmissionValidationError, match="saved"):
        _build(dataset)


def test_malformed_sibling_is_skipped_when_not_required(dataset, test_session_plan):
    other = Dataset.objects.create(deposition=dataset.deposition, title="Broken", dataset_id=303)
    session = DepositionSession.objects.create(
        dataset=other,
        msi_session=MsiSession.objects.create(name="24dec02", session_plan=test_session_plan),
        aretomo_run_name="run009",
    )
    TiltseriesMetadata.objects.create(session=session, autofill_metadata={"paths": {"aretomo3": "/a"}})  # malformed
    config = build_dataprep_config(dataset.deposition, output_dir="/staging/101", required_dataset_ids={202})
    assert set(config["datasets"]) == {"dataset_202"}


def test_required_dataset_without_autofill_raises(dataset):
    TiltseriesMetadata.objects.filter(session__dataset=dataset).delete()
    with pytest.raises(SubmissionValidationError, match="no usable autofill"):
        build_dataprep_config(dataset.deposition, output_dir="/staging/101", required_dataset_ids={202})


def test_required_dataset_without_sessions_raises(dataset):
    dataset.sessions.all().delete()
    with pytest.raises(SubmissionValidationError, match="no usable autofill"):
        build_dataprep_config(dataset.deposition, output_dir="/staging/101", required_dataset_ids={202})


def test_unrequired_draft_sibling_is_skipped(dataset):
    Dataset.objects.create(deposition=dataset.deposition, title="Draft", dataset_id=303)  # no sessions
    config = build_dataprep_config(dataset.deposition, output_dir="/staging/101", required_dataset_ids={202})
    assert set(config["datasets"]) == {"dataset_202"}


def test_malformed_required_dataset_still_raises(dataset):
    metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
    metadata.autofill_metadata = {"paths": {"aretomo3": "/a"}}
    metadata.save()
    with pytest.raises(SubmissionValidationError, match="saved"):
        build_dataprep_config(dataset.deposition, output_dir="/staging/101", required_dataset_ids={202})


@pytest.mark.parametrize("output_dir", [None, "", "relative/path"])
def test_rejects_invalid_output_dir(dataset, output_dir):
    with pytest.raises(SubmissionValidationError, match="absolute cluster path"):
        build_dataprep_config(dataset.deposition, output_dir=output_dir)


@pytest.mark.parametrize("destination", ["", "/local/path", "s3://", "s3:///missing-bucket"])
def test_rejects_invalid_destination(dataset, destination):
    with pytest.raises(SubmissionValidationError, match="S3 destination"):
        _build(dataset, sync_destination=destination)


def test_config_uses_institution_destination_from_pathtype(dataset):
    PathType.objects.filter(data_kind__data_type="deposition_sync_destination", cluster=None).update(
        overlay_path="s3://another-institution/depositions/"
    )
    assert _build(dataset)["sync_destination"] == "s3://another-institution/depositions"


def test_invalid_configured_destination_is_rejected(dataset):
    PathType.objects.filter(data_kind__data_type="deposition_sync_destination", cluster=None).update(
        overlay_path="/local/path"
    )
    with pytest.raises(SubmissionValidationError, match="S3 destination"):
        _build(dataset)
