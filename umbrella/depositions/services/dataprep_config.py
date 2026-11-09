"""Build the prep deployment config from saved autofill data and reviewed DB values.

This is dataprep_config.yaml, separate from the portal metadata built by dataset_metadata.
Path resolution, remote writes, and launching jobs belong to the submit service.
"""

from copy import deepcopy
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import yaml
from stores.paths import resolve_dir

from depositions.models import Deposition, TiltseriesMetadata
from depositions.services.annotation_config import session_annotations
from depositions.services.dataset_metadata import build_dataset_metadata, build_deposition_metadata
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.subset import selected_positions


def _validate_sync_destination(destination):
    if not isinstance(destination, str) or not destination.startswith("s3://") or not urlsplit(destination).netloc:
        raise SubmissionValidationError("sync_destination must be an S3 destination.")
    return destination.rstrip("/")


def resolve_sync_destination(*, cluster=None):
    return _validate_sync_destination(resolve_dir("deposition_sync_destination", cluster=cluster))


# These fields were mapped from init during autofill; current DB values take precedence.
ACQUISITION_FIELDS = {
    "pixel_spacing": "pixel_spacing",
    "acceleration_voltage_kv": "acceleration_voltage",
    "spherical_aberration_constant": "spherical_aberration_constant",
}


def _session_config(session, authors):
    name = session.msi_session.name
    try:
        metadata = session.tiltseries_metadata
    except TiltseriesMetadata.DoesNotExist:
        raise SubmissionValidationError(f"Session {name!r} needs autofill before preparing the dataset.")

    raw = metadata.autofill_metadata
    if not isinstance(raw, dict) or not raw:
        raise SubmissionValidationError(f"Session {name!r} has no saved autofill config.")
    paths = raw.get("paths")
    if not isinstance(paths, dict) or not paths.get("aretomo3"):
        raise SubmissionValidationError(f"Session {name!r} has no saved AreTomo source path.")
    if not isinstance(raw.get("acquisition"), dict):
        raise SubmissionValidationError(f"Session {name!r} has no saved acquisition config.")

    config = deepcopy(raw)
    annotations = session_annotations(session, authors)
    if annotations:
        config["annotations"] = annotations
    for config_field, model_field in ACQUISITION_FIELDS.items():
        config["acquisition"][config_field] = getattr(metadata, model_field)
    by_flavor = {tomo.flavor: tomo for tomo in session.tomogram_metadata.all()}
    # Autofill maps these acquisition values onto the filtered reconstruction.
    filtered = by_flavor.get("filtered")
    if filtered is not None:
        config["acquisition"]["aretomo_version"] = filtered.reconstruction_software
        if filtered.voxel_spacing is None:
            config["acquisition"]["binned_voxel_ratio"] = None
        else:
            if metadata.pixel_spacing is None or metadata.pixel_spacing <= 0 or filtered.voxel_spacing <= 0:
                raise SubmissionValidationError(f"Session {name!r} needs positive pixel and voxel spacing.")
            config["acquisition"]["binned_voxel_ratio"] = filtered.voxel_spacing / metadata.pixel_spacing
    config["tilt_axis_angle"] = metadata.tilt_axis
    config["total_dose"] = metadata.total_flux

    # Per-flavor overrides; the tool falls back to `acquisition` for anything absent.
    tomograms = {}
    for flavor, tomo in by_flavor.items():
        entry = {"is_visualization_default": tomo.is_visualization_default}
        # ctf_corrected is nullable; the tool rejects a null, so only send a real bool.
        if tomo.ctf_corrected is not None:
            entry["ctf_corrected"] = tomo.ctf_corrected
        if tomo.voxel_spacing is not None:
            entry["voxel_spacing"] = tomo.voxel_spacing
        # processing is omitted: the tool derives it from the flavor.
        for field in ("reconstruction_software", "reconstruction_method", "processing_software"):
            value = getattr(tomo, field)
            if value:
                entry[field] = value
        tomograms[flavor] = entry
    if tomograms:
        config["tomograms"] = tomograms
    return config


def _session_has_autofill(session):
    try:
        raw = session.tiltseries_metadata.autofill_metadata
    except TiltseriesMetadata.DoesNotExist:
        return False
    return isinstance(raw, dict) and bool(raw)


def dataset_is_ready(dataset):
    sessions = list(dataset.sessions.select_related("tiltseries_metadata"))
    return bool(sessions) and all(_session_has_autofill(s) for s in sessions)


def require_custom_positions(session) -> list[str]:
    """Positions to keep for a custom-mode session; raise if it has no usable selection or uses an
    unsupported cluster CSV path. Shared by submit (pre-claim) and the config builder (backstop)."""
    name = session.msi_session.name
    if session.subset_csv_path:
        raise SubmissionValidationError(
            f"Session {name} uses a cluster CSV path for its subset, which isn't supported yet - "
            "re-upload the selection in the Sources step."
        )
    positions = selected_positions(session.subset_selection)
    if not positions:
        raise SubmissionValidationError(f"Session {name} has no custom subset selected.")
    return positions


def _dataset_block(dataset):
    if dataset.dataset_id is None:
        raise SubmissionValidationError("Reserve the dataset_id before preparing the dataset.")
    metadata = build_dataset_metadata(dataset)
    sessions = {}
    selected_sessions = (
        dataset.sessions.select_related("msi_session", "tiltseries_metadata")
        .prefetch_related("tomogram_metadata")
        .order_by("msi_session__name")
    )
    for session in selected_sessions:
        config = _session_config(session, metadata.get("authors", []))
        if dataset.tomogram_subset_mode == "custom":
            # Custom selections must not fall back to processing all positions.
            config["positions"] = require_custom_positions(session)
        sessions[session.msi_session.name] = config
    if not sessions:
        raise SubmissionValidationError("Select at least one session before preparing the dataset.")
    return {"dataset_id": dataset.dataset_id, "metadata": metadata, "sessions": sessions}


def is_defining_dataset(dataset) -> bool:
    """Include metadata until an upload succeeds, then only for its persisted owner."""
    owner = (
        Deposition.objects.using(dataset._state.db)
        .filter(pk=dataset.deposition_id)
        .values_list("metadata_dataset_id", flat=True)
        .get()
    )
    return owner is None or owner == dataset.pk


def build_dataprep_config(dataset, *, output_dir, sync_destination=None):
    """Build this dataset's prep config with its deposition ID and any defining metadata."""
    deposition = dataset.deposition
    if deposition.deposition_id is None:
        raise SubmissionValidationError("Reserve the deposition_id before preparing.")
    output_dir = str(output_dir) if output_dir is not None else ""
    if not output_dir or not PurePosixPath(output_dir).is_absolute():
        raise SubmissionValidationError("output_dir must be an absolute cluster path.")
    sync_destination = (
        resolve_sync_destination() if sync_destination is None else _validate_sync_destination(sync_destination)
    )
    if not dataset_is_ready(dataset):
        raise SubmissionValidationError(
            f"Dataset {dataset.dataset_id} isn't ready to prepare; add sessions and run auto-fill first."
        )
    block = _dataset_block(dataset)
    if is_defining_dataset(dataset):
        block["deposition_metadata"] = build_deposition_metadata(deposition)
    return {
        "output_dir": output_dir,
        "sync_destination": sync_destination,
        "deposition_id": deposition.deposition_id,
        # Preserve sibling dataset directories.
        "shared_deposition": True,
        "datasets": {f"dataset_{dataset.dataset_id}": block},
    }


def dataprep_config_yaml(dataset, *, output_dir, sync_destination=None):
    """Render the prep deployment config as YAML for a later remote write."""
    config = build_dataprep_config(dataset, output_dir=output_dir, sync_destination=sync_destination)
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True, default_flow_style=False)
