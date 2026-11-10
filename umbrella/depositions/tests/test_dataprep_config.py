"""Deployment-config generation uses saved data without init, SSH, or SLURM."""

from copy import deepcopy
from types import SimpleNamespace
from unittest import mock

import pytest
import yaml
from django.core.exceptions import ImproperlyConfigured
from people.models import Person
from processes.models import Pipe, PipeExecution, PipeInPlan, ProcRun, ProcSoftware
from processes.services.cluster_resolver import get_default_cluster_id
from stores.models import Cluster, DataKind, PathType
from tem.models import MsiSession

from depositions.models import (
    Dataset,
    DatasetJob,
    Deposition,
    DepositionAnnotation,
    DepositionAnnotationMethodLink,
    DepositionSession,
    TiltseriesMetadata,
    TomogramMetadata,
)
from depositions.services import annotation_config
from depositions.services.dataprep_config import (
    build_dataprep_config,
    dataprep_config_yaml,
)
from depositions.services.dataset_metadata import build_deposition_metadata
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.submission import on_push_complete

RAW_SESSION = {
    "paths": {
        "aretomo3": "/hpc/aretomo3/24nov10/run001",
        "mdoc": "/hpc/mdoc/24nov10",
        "frames": "/hpc/frames/24nov10",
        "gain": "/hpc/gains/reference.gain",
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
        dataset=dataset, msi_session=test_msi_session, aretomo_run_name="run001", denoise_run_name=""
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
    return build_dataprep_config(dataset, output_dir="/staging/101", **kwargs)


def _session(config, name="24nov10"):
    return config["datasets"]["dataset_202"]["sessions"][name]


def test_builds_deployment_config_with_reserved_ids(dataset):
    config = _build(dataset)
    assert config["output_dir"] == "/staging/101"
    assert config["deposition_id"] == 101
    assert config["sync_destination"] == "s3://cryoetportal-biohub-hpc-globus/CZII"
    # Single-dataset config in the shared dir; the flag stops sync from deleting siblings.
    assert config["shared_deposition"] is True
    assert config["datasets"]["dataset_202"]["dataset_id"] == 202
    assert _session(config) == RAW_SESSION
    metadata = config["datasets"]["dataset_202"]["metadata"]
    assert metadata["dataset_title"] == dataset.title


@pytest.fixture
def denoise_dataset(dataset):
    Cluster.objects.create(cluster_id="c1", name="C1", is_active=True)
    root = PathType.objects.create(
        data_kind=DataKind.objects.create(data_type="test_denoise_root"),
        overlay_path="/custom/{proc_software}/",
    )
    ProcSoftware.objects.update_or_create(
        processor_class="denoiset",
        defaults={"name": "denoise", "storage_dirname": "denoise", "processing_root": root},
    )
    session = dataset.sessions.get()
    session.denoise_run_name = "005"
    session.save(update_fields=["denoise_run_name"])
    return dataset


def _record_execution(session, plan, processor_class, run, cluster_id):
    software, _ = ProcSoftware.objects.get_or_create(
        processor_class=processor_class, defaults={"name": processor_class}
    )
    pipe = Pipe.objects.create(name=processor_class, software=software)
    step = PipeInPlan.objects.create(plan=plan, pipe=pipe, step=1, name=processor_class)
    proc_run = ProcRun.objects.create(name=run, proc_plan=plan, msi_session=session.msi_session)
    return PipeExecution.objects.create(proc_run=proc_run, pipe_in_plan=step, parameters={"cluster_id": cluster_id})


def test_denoise_source_resolved_from_selected_run(denoise_dataset):
    session = denoise_dataset.sessions.get()
    with mock.patch("depositions.services.dataprep_config.cluster_id_for_run", return_value="c1") as lookup:
        config = _build(denoise_dataset)
    assert _session(config)["paths"]["denoise"] == "/custom/denoise/24nov10/run005"
    assert lookup.call_args_list == [
        mock.call(session.msi_session.name, "run001", processor_class="aretomo3"),
        mock.call(session.msi_session.name, "run005", default="c1", processor_class="denoiset"),
    ]


@pytest.mark.parametrize("denoise_run", ["005", "run005"])
def test_denoise_missing_execution_falls_back_to_prep_cluster(denoise_dataset, test_proc_plan, denoise_run):
    session = denoise_dataset.sessions.get()
    session.aretomo_run_name = "001"
    session.denoise_run_name = denoise_run
    session.save()
    assert get_default_cluster_id() != "c1"
    _record_execution(session, test_proc_plan, "aretomo3", "run001", "c1")
    # An unrelated execution with the denoise run's name must not determine its cluster.
    _record_execution(session, test_proc_plan, "aretomo3", "run005", get_default_cluster_id())
    ProcSoftware.objects.filter(processor_class="denoiset").update(processing_root=None)
    PathType.objects.update_or_create(
        data_kind=DataKind.objects.get(data_type="processing_root"),
        cluster=Cluster.objects.get(cluster_id="c1"),
        defaults={"overlay_path": "/cluster-c1/{proc_software}"},
    )
    config = _build(denoise_dataset)
    assert _session(config)["paths"]["denoise"] == "/cluster-c1/denoise/24nov10/run005"


def test_denoise_on_another_cluster_is_rejected(denoise_dataset, test_proc_plan):
    session = denoise_dataset.sessions.get()
    _record_execution(session, test_proc_plan, "aretomo3", "run001", "c1")
    _record_execution(session, test_proc_plan, "denoiset", "run005", "c2")
    with pytest.raises(SubmissionValidationError, match="denoise run 'run005'.*'c2'.*AreTomo cluster 'c1'"):
        _build(denoise_dataset)


@pytest.mark.parametrize("error", [ImproperlyConfigured("No denoise root"), PathType.DoesNotExist("Missing root")])
def test_misconfigured_denoise_raises_actionable_error(denoise_dataset, error, caplog):
    with (
        mock.patch("depositions.services.dataprep_config.cluster_id_for_run", return_value="c1"),
        mock.patch("depositions.services.dataprep_config.get_processor") as processor,
    ):
        processor.return_value.get_processing_base_path.side_effect = error
        with pytest.raises(SubmissionValidationError) as raised:
            _build(denoise_dataset)
        assert raised.value.public_message == "Denoise isn't configured on this cluster."
        assert str(error) not in raised.value.public_message
    record = next(record for record in caplog.records if record.exc_info)
    assert record.name == "depositions.services.dataprep_config"
    assert record.levelname == "ERROR"
    assert "session '24nov10' on cluster 'c1'" in record.getMessage()
    assert record.exc_info[1] is error
    assert str(error) in caplog.text


def test_skipped_denoise_drops_the_source_path(dataset):
    session = dataset.sessions.get()  # fixture has denoise_run_name=""
    # Even a stale saved denoise path is dropped when denoise is skipped.
    session.tiltseries_metadata.autofill_metadata["paths"]["denoise"] = "/stale/run009"
    session.tiltseries_metadata.save(update_fields=["autofill_metadata"])
    assert "denoise" not in _session(_build(dataset))["paths"]


def test_config_contains_only_the_built_dataset(dataset, test_session_plan):
    # A sibling in the same deposition must not leak into this dataset's config.
    other = Dataset.objects.create(deposition=dataset.deposition, title="Dataset 2", dataset_id=303)
    session = DepositionSession.objects.create(
        dataset=other,
        msi_session=MsiSession.objects.create(name="24dec01", session_plan=test_session_plan),
        aretomo_run_name="run009",
    )
    TiltseriesMetadata.objects.create(session=session, autofill_metadata=deepcopy(RAW_SESSION), pixel_spacing=1.54)
    assert set(_build(dataset)["datasets"]) == {"dataset_202"}
    assert set(_build(other)["datasets"]) == {"dataset_303"}


def test_deposition_metadata_rides_under_the_built_dataset(dataset):
    dataset.deposition.description = "A deposition."
    dataset.deposition.deposition_publications = "https://doi.org/10.1/x"
    dataset.deposition.save()
    block = _build(dataset)["datasets"]["dataset_202"]["deposition_metadata"]
    assert block["deposition_title"] == dataset.deposition.title
    assert block["deposition_description"] == "A deposition."
    assert block["cross_references"] == {"publications": "https://doi.org/10.1/x"}
    assert "authors" in block
    assert set(block["dates"]) >= {"deposition_date", "last_modified_date"}
    assert block["deposition_types"] == ["dataset"]


def test_deposition_types_include_annotation_when_selected(dataset):
    session = dataset.sessions.get()
    DepositionAnnotation.objects.create(session=session, copick_kind="picks", copick_ref="ribosome:alice/0")
    assert build_deposition_metadata(dataset.deposition)["deposition_types"] == ["dataset", "annotation"]


def test_only_the_upload_owner_carries_deposition_metadata(dataset, test_session_plan):
    other = Dataset.objects.create(deposition=dataset.deposition, title="Dataset 2", dataset_id=303)
    session = DepositionSession.objects.create(
        dataset=other,
        msi_session=MsiSession.objects.create(name="24dec01", session_plan=test_session_plan),
        aretomo_run_name="run009",
    )
    TiltseriesMetadata.objects.create(session=session, autofill_metadata=deepcopy(RAW_SESSION), pixel_spacing=1.54)
    assert "deposition_metadata" in _build(dataset)["datasets"]["dataset_202"]
    assert "deposition_metadata" in _build(other)["datasets"]["dataset_303"]
    job = DatasetJob.objects.create(dataset=other, state="push_running", push_slurm_job_id="push-other")
    on_push_complete(job, True, job_id="push-other")
    dataset.deposition.refresh_from_db()
    assert "deposition_metadata" not in _build(dataset)["datasets"]["dataset_202"]
    assert "deposition_metadata" in _build(other)["datasets"]["dataset_303"]
    assert _build(dataset)["deposition_id"] == _build(other)["deposition_id"] == 101


def test_deleted_metadata_owner_can_be_replaced(dataset, test_session_plan):
    other = Dataset.objects.create(deposition=dataset.deposition, title="Draft", dataset_id=101)
    job = DatasetJob.objects.create(dataset=dataset, state="push_running", push_slurm_job_id="push-first")
    on_push_complete(job, True, job_id="push-first")
    dataset.deposition.refresh_from_db()
    session = DepositionSession.objects.create(
        dataset=other,
        msi_session=MsiSession.objects.create(name="24dec01", session_plan=test_session_plan),
        aretomo_run_name="run009",
    )
    TiltseriesMetadata.objects.create(session=session, autofill_metadata=deepcopy(RAW_SESSION), pixel_spacing=1.54)
    assert "deposition_metadata" not in _build(other)["datasets"]["dataset_101"]
    assert "deposition_metadata" in _build(dataset)["datasets"]["dataset_202"]
    dataset.delete()
    other.deposition.refresh_from_db()
    assert "deposition_metadata" in _build(other)["datasets"]["dataset_101"]


def test_custom_positions_are_per_session_and_omitted_outside_custom_mode(dataset, test_session_plan):
    session = dataset.sessions.get()
    session.subset_selection = {"Selected positions": ["Position_1.mrc"]}
    session.save()
    other = DepositionSession.objects.create(
        dataset=dataset,
        msi_session=MsiSession.objects.create(name="24dec01", session_plan=test_session_plan),
        aretomo_run_name="run009",
        subset_selection=[{"Tilt_Series": "Position_2.mrc"}],
    )
    TiltseriesMetadata.objects.create(session=other, autofill_metadata=deepcopy(RAW_SESSION), pixel_spacing=1.54)
    dataset.tomogram_subset_mode = "custom"
    dataset.save()
    config = _build(dataset)
    assert _session(config)["positions"] == ["Position_1"]
    assert _session(config, "24dec01")["positions"] == ["Position_2"]

    dataset.tomogram_subset_mode = "all"
    dataset.save()
    config = _build(dataset)
    assert "positions" not in _session(config)
    assert "positions" not in _session(config, "24dec01")


def test_custom_mode_rejects_an_empty_selection(dataset):
    """Empty positions in custom mode would mean "process all" to the CLI, so it must be rejected
    at config build - not silently omitted - which also stops a shared-session sibling leaking."""
    dataset.tomogram_subset_mode = "custom"
    dataset.save()
    with pytest.raises(SubmissionValidationError, match="no custom subset selected"):
        _build(dataset)


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


def test_emits_per_flavor_tomogram_block(dataset):
    session = dataset.sessions.get()
    TomogramMetadata.objects.create(
        session=session,
        flavor="denoised",
        voxel_spacing=4.995,
        reconstruction_software="AreTomo3 2.1.0",
        reconstruction_method="WBP",
        ctf_corrected=True,
        processing="denoised",
        processing_software="DenoisET",
        is_visualization_default=True,
    )
    TomogramMetadata.objects.create(
        session=session,
        flavor="filtered",
        voxel_spacing=9.99,
        processing="filtered",
        processing_software="AreTomo3 2.1.0",
        is_visualization_default=False,
    )
    tomograms = _session(_build(dataset))["tomograms"]
    assert tomograms["denoised"]["voxel_spacing"] == 4.995
    assert tomograms["filtered"]["voxel_spacing"] == 9.99
    assert tomograms["denoised"]["processing_software"] == "DenoisET"
    assert tomograms["denoised"]["is_visualization_default"] is True
    assert tomograms["filtered"]["is_visualization_default"] is False
    # `processing` is derived from the flavor by the tool, so it must not be emitted here.
    assert "processing" not in tomograms["denoised"]
    # Nullable ctf_corrected is only sent when set; the tool rejects a null.
    assert tomograms["denoised"]["ctf_corrected"] is True
    assert "ctf_corrected" not in tomograms["filtered"]


def test_no_per_flavor_block_without_tomogram_rows(dataset):
    assert "tomograms" not in _session(_build(dataset))


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
    text = dataprep_config_yaml(dataset, output_dir="/staging/101", sync_destination="s3://test-bucket/review")
    parsed = yaml.safe_load(text)
    assert list(parsed["datasets"]["dataset_202"]["sessions"]) == ["24nov10", "24nov11"]
    assert _session(parsed, "24nov11")["paths"]["aretomo3"] == raw["paths"]["aretomo3"]
    assert _session(parsed, "24nov11")["acquisition"]["pixel_spacing"] == 2
    assert parsed["sync_destination"] == "s3://test-bucket/review"
    assert parsed["datasets"]["dataset_202"]["metadata"]["dataset_title"] == dataset.title


@pytest.mark.parametrize("missing_id", ["deposition", "dataset"])
def test_rejects_missing_reservations(dataset, missing_id):
    if missing_id == "deposition":
        dataset.deposition.deposition_id = None
    else:
        dataset.dataset_id = None
    with pytest.raises(SubmissionValidationError, match="Reserve"):
        build_dataprep_config(dataset, output_dir="/staging/101")


@pytest.mark.parametrize(
    "missing,raw",
    [
        pytest.param("sessions", None, id="no-sessions"),
        pytest.param("autofill", None, id="no-autofill-record"),
        pytest.param(None, {}, id="empty-autofill-mapping"),
        pytest.param(None, "invalid", id="invalid-autofill-string"),
        pytest.param(None, [], id="empty-autofill-list"),
    ],
)
def test_rejects_dataset_not_ready_to_prepare(dataset, missing, raw):
    if missing == "sessions":
        dataset.sessions.all().delete()
    elif missing == "autofill":
        TiltseriesMetadata.objects.filter(session__dataset=dataset).delete()
    else:
        metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
        metadata.autofill_metadata = raw
        metadata.save()
    with pytest.raises(SubmissionValidationError, match="ready to prepare"):
        _build(dataset)


@pytest.mark.parametrize("raw", [{"paths": {}}, {"paths": {"aretomo3": "/a"}}])
def test_rejects_malformed_saved_autofill(dataset, raw):
    metadata = TiltseriesMetadata.objects.get(session__dataset=dataset)
    metadata.autofill_metadata = raw
    metadata.save()
    with pytest.raises(SubmissionValidationError, match="saved"):
        _build(dataset)


@pytest.mark.parametrize("output_dir", [None, "", "relative/path"])
def test_rejects_invalid_output_dir(dataset, output_dir):
    with pytest.raises(SubmissionValidationError, match="absolute cluster path"):
        build_dataprep_config(dataset, output_dir=output_dir)


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


@pytest.mark.parametrize("kind,expected", [("picks", "picks"), ("segmentations", "segmentation_mask")])
def test_selected_annotations_use_sync_contract_and_reviewed_authors(dataset, monkeypatch, kind, expected):
    author = Person.objects.create(given_name="Ada", family_name="")
    dataset.deposition.authors_json = [{"author_id": author.pk, "is_primary": True, "is_corresponding": True}]
    dataset.deposition.save()
    session = dataset.sessions.get()
    session.selected_copick_runs = ["run003", "run004"]
    session.save()
    TomogramMetadata.objects.create(session=session, flavor="filtered", voxel_spacing=12, is_visualization_default=True)
    selected = DepositionAnnotation.objects.create(
        session=session,
        copick_kind=kind,
        copick_ref="ribosome:alice/0",
        object_id="GO:0022626",
        object_name="ribosome",
        annotation_method="Manual annotation",
        annotation_software="Copick",
        method_type="manual",
        ground_truth_status=True,
    )
    DepositionAnnotationMethodLink.objects.create(
        annotation=selected, link_type="source_code", link="https://example.org/code"
    )
    cluster_kwargs = {}
    monkeypatch.setattr(
        annotation_config, "cluster_id_for_run", lambda *a, **k: cluster_kwargs.update(k) or "cluster-a"
    )
    monkeypatch.setattr(
        annotation_config, "get_processor", lambda _: SimpleNamespace(get_processing_base_path=lambda **kw: "/copick")
    )
    annotations = _session(_build(dataset))["annotations"]
    assert cluster_kwargs["processor_class"] == "aretomo3"
    assert len(annotations) == 1
    entry = annotations[0]
    assert entry["kind"] == expected and entry["copick_ref"] == "ribosome:alice/0"
    assert entry["copick_config"] == ["/copick/24nov10/run003/config.json", "/copick/24nov10/run004/config.json"]
    assert entry["voxel_spacing"] == 12
    assert entry["authors"] == [{"name": "Ada", "primary_author_status": True, "corresponding_author_status": True}]
    assert entry["method_links"] == [{"link_type": "source_code", "link": "https://example.org/code"}]

    selected.is_selected = False
    selected.save(update_fields=["is_selected"])
    assert "annotations" not in _session(_build(dataset))


@pytest.mark.parametrize("problem,match", [("mesh", "mesh"), ("spacing", "voxel spacing")])
def test_annotation_export_rejects_unsupported_or_incomplete_selections(dataset, problem, match):
    session = dataset.sessions.get()
    session.selected_copick_runs = ["run003"]
    session.save()
    if problem != "spacing":
        TomogramMetadata.objects.create(session=session, flavor="filtered", voxel_spacing=12)
    DepositionAnnotation.objects.create(
        session=session, copick_kind="meshes" if problem == "mesh" else "picks", copick_ref="ribosome:alice/0"
    )
    with pytest.raises(SubmissionValidationError, match=match):
        _build(dataset)
