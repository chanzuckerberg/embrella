"""Build the prep deployment config from saved autofill data and reviewed DB values.

This is dataprep_config.yaml, separate from the portal metadata YAML in config_yaml.
Path resolution, remote writes, and launching jobs belong to the submit service.
"""

from copy import deepcopy
from pathlib import PurePosixPath

import yaml

from depositions.models import TiltseriesMetadata

DEFAULT_SYNC_DESTINATION = "s3://cryoetportal-biohub-hpc-globus/CZII"

# These fields were mapped from init during autofill; current DB values take precedence.
ACQUISITION_FIELDS = {
    "pixel_spacing": "pixel_spacing",
    "acceleration_voltage_kv": "acceleration_voltage",
    "spherical_aberration_constant": "spherical_aberration_constant",
}


def _session_config(session):
    name = session.msi_session.name
    try:
        metadata = session.tiltseries_metadata
    except TiltseriesMetadata.DoesNotExist:
        raise ValueError(f"Session {name!r} needs autofill before preparing the dataset.")

    raw = metadata.autofill_metadata
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"Session {name!r} has no saved autofill config.")
    paths = raw.get("paths")
    if not isinstance(paths, dict) or not paths.get("aretomo3"):
        raise ValueError(f"Session {name!r} has no saved AreTomo source path.")
    if not isinstance(raw.get("acquisition"), dict):
        raise ValueError(f"Session {name!r} has no saved acquisition config.")

    config = deepcopy(raw)
    for config_field, model_field in ACQUISITION_FIELDS.items():
        config["acquisition"][config_field] = getattr(metadata, model_field)
    # Autofill maps these acquisition values onto the filtered reconstruction.
    filtered = next((tomo for tomo in session.tomogram_metadata.all() if tomo.flavor == "filtered"), None)
    if filtered is not None:
        config["acquisition"]["aretomo_version"] = filtered.reconstruction_software
        if filtered.voxel_spacing is None:
            config["acquisition"]["binned_voxel_ratio"] = None
        else:
            if metadata.pixel_spacing is None or metadata.pixel_spacing <= 0 or filtered.voxel_spacing <= 0:
                raise ValueError(f"Session {name!r} needs positive pixel and voxel spacing.")
            config["acquisition"]["binned_voxel_ratio"] = filtered.voxel_spacing / metadata.pixel_spacing
    config["tilt_axis_angle"] = metadata.tilt_axis
    config["total_dose"] = metadata.total_flux
    return config


def build_dataprep_config(dataset, *, output_dir, sync_destination=DEFAULT_SYNC_DESTINATION):
    """Build one dataset's deployment config without running init."""
    if dataset.deposition.deposition_id is None or dataset.dataset_id is None:
        raise ValueError("Reserve deposition_id and dataset_id before preparing the dataset.")
    output_dir = str(output_dir) if output_dir is not None else ""
    if not output_dir or not PurePosixPath(output_dir).is_absolute():
        raise ValueError("output_dir must be an absolute cluster path.")
    if not isinstance(sync_destination, str) or not sync_destination.startswith("s3://"):
        raise ValueError("sync_destination must be an S3 destination.")

    sessions = {}
    selected_sessions = (
        dataset.sessions.select_related("msi_session", "tiltseries_metadata")
        .prefetch_related("tomogram_metadata")
        .order_by("msi_session__name")
    )
    for session in selected_sessions:
        name = session.msi_session.name
        sessions[name] = _session_config(session)
    if not sessions:
        raise ValueError("Select at least one session before preparing the dataset.")

    return {
        "output_dir": output_dir,
        "sync_destination": sync_destination,
        "deposition_id": dataset.deposition.deposition_id,
        "datasets": {
            f"dataset_{dataset.dataset_id}": {
                "dataset_id": dataset.dataset_id,
                "sessions": sessions,
            },
        },
    }


def dataprep_config_yaml(dataset, *, output_dir, sync_destination=DEFAULT_SYNC_DESTINATION):
    """Render the prep deployment config as YAML for a later remote write."""
    config = build_dataprep_config(dataset, output_dir=output_dir, sync_destination=sync_destination)
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True, default_flow_style=False)
