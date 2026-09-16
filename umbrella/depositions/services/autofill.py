"""Auto-fill a session's tiltseries/tomogram metadata via ``cryoetportalprep init``."""

import logging
import shlex
import uuid
from typing import TYPE_CHECKING

import yaml
from stores.models import PathType
from stores.paths import resolve_dir

from common import clusterio

if TYPE_CHECKING:
    from tem.models import SessionPlan

logger = logging.getLogger(__name__)

# Width of the microscope_image_corrector column.
_IMAGE_CORRECTOR_MAXLEN = 256

# Markers so we can pull the config YAML out of noisy conda/click stdout.
_YAML_BEGIN = "AUTOFILL_YAML_BEGIN"
_YAML_END = "AUTOFILL_YAML_END"


def run_autofill_init(cluster_id: str, aretomo3_dir: str, session_name: str, *, timeout: int = 180) -> dict:
    """SSH to ``cluster_id``, run ``cryoetportalprep init``, return the parsed session block."""
    try:
        dataportal_env = resolve_dir("dataportal_env", cluster=cluster_id)
    except PathType.DoesNotExist:
        logger.error("autofill: dataportal_env PathType not configured (cluster=%s)", cluster_id)
        return {"filled": False, "session": None, "reason": "dataportal_env_unconfigured"}

    try:
        ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id)
    except clusterio.SSHDisabledError:
        return {"filled": False, "session": None, "reason": "ssh_disabled"}
    except Exception:
        logger.exception("autofill: SSH connect failed for cluster %s", cluster_id)
        return {"filled": False, "session": None, "reason": "ssh_error"}

    out_dir = f"/tmp/dep_autofill_{uuid.uuid4().hex}"

    cmd = (
        f"ml load anaconda 2>/dev/null; "
        f"conda activate {shlex.quote(dataportal_env)} && "
        f"mkdir -p {shlex.quote(out_dir)} && "
        f"cryoetportalprep init -a {shlex.quote(str(aretomo3_dir))} "
        f"-s {shlex.quote(session_name)} -o {shlex.quote(out_dir)} 1>&2 && "
        f"echo {_YAML_BEGIN} && cat {shlex.quote(out_dir)}/dataprep_config.yaml && echo {_YAML_END}; "
        f"rm -rf {shlex.quote(out_dir)}"
    )
    try:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace").strip()

        block = _between(out, _YAML_BEGIN, _YAML_END)
        if block is None:
            logger.error("autofill: no config emitted for %s. stderr=%s", session_name, err[:500])
            return {"filled": False, "session": None, "reason": _short_reason(err)}

        session = _extract_session(yaml.safe_load(block), session_name)
        if session is None:
            logger.error("autofill: session %s missing from emitted config", session_name)
            return {"filled": False, "session": None, "reason": "session_not_in_config"}
        return {"filled": True, "session": session, "reason": None}
    except Exception:
        logger.exception("autofill init failed for %s on %s", session_name, cluster_id)
        return {"filled": False, "session": None, "reason": "init_error"}
    finally:
        ssh.close()


def map_session_to_metadata(session: dict | None) -> dict:
    """Map a ``dataprep_config.yaml`` session block to ``{tiltseries, tomograms}`` field dicts."""
    session = session or {}
    acq = session.get("acquisition") or {}
    tiltseries = _compact(
        {
            "pixel_spacing": acq.get("pixel_spacing"),
            "acceleration_voltage": acq.get("acceleration_voltage_kv"),
            "spherical_aberration_constant": acq.get("spherical_aberration_constant"),
            "total_flux": session.get("total_dose"),
            "tilt_axis": session.get("tilt_axis_angle"),
            "binning_from_frames": acq.get("binned_voxel_ratio"),
        }
    )
    aretomo_version = acq.get("aretomo_version")
    shared = _compact(
        {
            "reconstruction_software": aretomo_version,
            "voxel_spacing": _voxel_spacing(acq.get("pixel_spacing"), acq.get("binned_voxel_ratio")),
        }
    )
    tomograms = [
        {
            **shared,
            "flavor": "denoised",
            "processing": "denoised",
            "processing_software": "DenoisET",
            "is_visualization_default": True,
        },
        {
            **shared,
            "flavor": "filtered",
            "processing": "filtered",
            "processing_software": aretomo_version or "",
            "is_visualization_default": False,
        },
    ]
    return {"tiltseries": tiltseries, "tomograms": tomograms}


def map_session_plan_to_instrument_metadata(session_plan: "SessionPlan") -> dict:
    """Instrument/facility fields from the session's Microscope/Camera + software (reads the ORM).

    Returns only non-blank values, so a blank tem column won't clobber what the user typed.
    """
    scope = session_plan.scope
    camera = session_plan.camera
    # image_correctors is raw JSON in admin: ignore a non-list, drop blanks, keep whole names within
    # the column (never slice mid-name into an invalid corrector).
    correctors = scope.image_correctors if isinstance(scope.image_correctors, (list, tuple)) else []
    names = [str(c).strip() for c in correctors if str(c).strip()]
    kept: list[str] = []
    for name in names:
        # Keep a contiguous prefix - stop at the first name that won't fit rather than reordering.
        if len(", ".join([*kept, name])) > _IMAGE_CORRECTOR_MAXLEN:
            break
        kept.append(name)
    if len(kept) < len(names):
        logger.warning(
            "image_correctors for %s truncated to fit the column: kept %d of %d", scope.name, len(kept), len(names)
        )
    image_corrector = ", ".join(kept)
    fields = {
        "microscope_manufacturer": scope.manufacturer,
        "microscope_model": scope.model,
        "microscope_energy_filter": scope.energy_filter,
        "microscope_phase_plate": scope.phase_plate,
        "microscope_image_corrector": image_corrector,
        "camera_manufacturer": camera.manufacturer,
        "camera_model": camera.model,
        "data_acquisition_software": session_plan.software.name,  # from the plan; filtered like the rest
    }
    return {k: v for k, v in fields.items() if v}


def _voxel_spacing(pixel_spacing, binned_voxel_ratio) -> float | None:
    if pixel_spacing is None or binned_voxel_ratio is None:
        return None
    return round(pixel_spacing * binned_voxel_ratio, 3)


def _compact(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _between(text: str, begin: str, end: str) -> str | None:
    """Return the lines strictly between the first ``begin`` and ``end`` marker lines."""
    lines = text.splitlines()
    try:
        i = lines.index(begin)
        j = lines.index(end, i + 1)
    except ValueError:
        return None
    return "\n".join(lines[i + 1 : j])


def _extract_session(cfg, session_name: str) -> dict | None:
    """Pull the named session block out of a (single-session) init config."""
    if not isinstance(cfg, dict):
        return None
    datasets = cfg.get("datasets") or {}
    for block in datasets.values():
        sessions = (block or {}).get("sessions") or {}
        if session_name in sessions:
            return sessions[session_name]
    # Fall back to the only session present.
    for block in datasets.values():
        sessions = (block or {}).get("sessions") or {}
        if len(sessions) == 1:
            return next(iter(sessions.values()))
    return None


def _short_reason(err: str) -> str:
    for line in reversed(err.splitlines()):
        stripped = line.strip()
        if stripped.startswith("Error:"):
            return stripped[len("Error:") :].strip()[:200]
    return "no_config_emitted"
