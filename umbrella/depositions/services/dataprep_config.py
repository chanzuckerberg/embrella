"""Build the prep deployment config from saved autofill data and reviewed DB values.

This is dataprep_config.yaml, separate from the portal metadata built by dataset_metadata.
Remote writes and launching jobs belong to the submit service.
"""

import logging
from copy import deepcopy
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import yaml
from django.core.exceptions import ImproperlyConfigured
from processes.services.cluster_resolver import cluster_id_for_run
from stores.models import Cluster, PathType
from stores.paths import resolve_dir
from workflow.processors import get_processor

from depositions.models import TiltseriesMetadata
from depositions.services.annotation_config import session_annotations
from depositions.services.dataset_metadata import build_dataset_metadata
from depositions.services.exceptions import SubmissionValidationError
from depositions.services.subset import selected_positions

logger = logging.getLogger(__name__)


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


def _apply_denoise_run(config, session):
    """Resolve the selected denoise run, requiring it to share the AreTomo prep cluster."""
    paths = config["paths"]
    run = (session.denoise_run_name or "").strip()
    if not run:
        paths.pop("denoise", None)
        return
    msi_session = session.msi_session
    run = run if run.startswith("run") else f"run{run}"
    aretomo_run = (session.aretomo_run_name or "").strip()
    aretomo_run = aretomo_run if aretomo_run.startswith("run") else f"run{aretomo_run}"
    prep_cluster_id = cluster_id_for_run(msi_session.name, aretomo_run, processor_class="aretomo3")
    cluster_id = cluster_id_for_run(msi_session.name, run, default=prep_cluster_id, processor_class="denoiset")
    if cluster_id != prep_cluster_id:
        raise SubmissionValidationError(
            f"Session {msi_session.name!r} denoise run {run!r} is on cluster {cluster_id!r}, "
            f"but preparation runs on AreTomo cluster {prep_cluster_id!r}. "
            "Select a denoise run on the preparation cluster."
        )
    try:
        cluster = Cluster.objects.get(cluster_id=cluster_id, is_active=True)
    except Cluster.DoesNotExist:
        raise SubmissionValidationError(f"Unknown cluster for session {msi_session.name!r}: {cluster_id}.")
    try:
        root = get_processor("denoiset").get_processing_base_path(cluster=cluster.cluster_id)
    except (ImproperlyConfigured, PathType.DoesNotExist) as exc:
        logger.exception("Cannot resolve denoise source for session %r on cluster %r.", msi_session.name, cluster_id)
        raise SubmissionValidationError("Denoise isn't configured on this cluster.") from exc
    paths["denoise"] = f"{root.rstrip('/')}/{msi_session.name}/{run}"


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
    _apply_denoise_run(config, session)
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


def build_dataprep_config(deposition, *, output_dir, sync_destination=None, required_dataset_ids=None):
    if deposition.deposition_id is None:
        raise SubmissionValidationError("Reserve the deposition_id before preparing.")
    output_dir = str(output_dir) if output_dir is not None else ""
    if not output_dir or not PurePosixPath(output_dir).is_absolute():
        raise SubmissionValidationError("output_dir must be an absolute cluster path.")
    sync_destination = (
        resolve_sync_destination() if sync_destination is None else _validate_sync_destination(sync_destination)
    )

    datasets = {}
    for dataset in deposition.datasets.order_by("dataset_id"):
        is_required = required_dataset_ids is None or dataset.dataset_id in required_dataset_ids
        if not dataset_is_ready(dataset):
            if required_dataset_ids is not None and dataset.dataset_id in required_dataset_ids:
                raise SubmissionValidationError(
                    f"Dataset {dataset.dataset_id} is staged or in flight but has no usable autofill; "
                    "fix it before submitting."
                )
            continue  # a draft/unready sibling has no tree to protect
        try:
            block = _dataset_block(dataset)
        except SubmissionValidationError:
            if is_required:
                raise
            logger.warning("Skipping malformed sibling dataset %s from the deposition config.", dataset.dataset_id)
            continue
        datasets[f"dataset_{dataset.dataset_id}"] = block
    if not datasets:
        raise SubmissionValidationError("No dataset in this deposition is ready to prepare.")

    return {
        "output_dir": output_dir,
        "sync_destination": sync_destination,
        "deposition_id": deposition.deposition_id,
        "datasets": datasets,
    }


def dataprep_config_yaml(deposition, *, output_dir, sync_destination=None, required_dataset_ids=None):
    """Render the prep deployment config as YAML for a later remote write."""
    config = build_dataprep_config(
        deposition, output_dir=output_dir, sync_destination=sync_destination, required_dataset_ids=required_dataset_ids
    )
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True, default_flow_style=False)
