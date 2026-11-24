"""Resolve a session's custom subset (an upload or a typed cluster CSV read over SFTP) into positions."""

import csv
import io
import logging

from common import clusterio
from depositions.models import TiltseriesMetadata
from depositions.services.cluster import deposition_cluster_id
from depositions.services.exceptions import SubmissionValidationError
from depositions.validators import ensure_safe_subset_csv_path

logger = logging.getLogger(__name__)

# A TiltSeries metrics CSV is tiny; the cap just stops a mistyped path to a huge file from filling memory.
MAX_SUBSET_CSV_MB = 10
MAX_SUBSET_CSV_BYTES = MAX_SUBSET_CSV_MB * 1024 * 1024


def selected_positions(subset_selection) -> list[str]:
    """The tilt-series positions to keep, or [] when there's no usable subset."""
    if isinstance(subset_selection, dict):
        values = subset_selection.get("Selected positions") or []
    elif isinstance(subset_selection, list):
        values = [row.get("Tilt_Series") for row in subset_selection if isinstance(row, dict)]
    else:
        return []
    positions = (str(value).strip().removesuffix(".mrc") for value in values if value)
    return [position for position in positions if position]


def positions_from_csv_text(text: str) -> list[str]:
    """Positions from a TiltSeries metrics CSV's ``Tilt_Series`` column (same shape an uploaded .csv
    is parsed into). lstrip drops an Excel BOM; newline="" lets csv handle CR/CRLF/LF itself."""
    return selected_positions(list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"), newline=""))))


def _aretomo_metrics_path(session) -> str:
    try:
        raw = session.tiltseries_metadata.autofill_metadata
    except TiltseriesMetadata.DoesNotExist:
        raw = None
    aretomo = raw.get("paths", {}).get("aretomo3") if isinstance(raw, dict) else None
    if not aretomo:
        raise SubmissionValidationError(f"Session {session.msi_session.name!r} has no saved AreTomo source path.")
    return f"{aretomo.rstrip('/')}/TiltSeries_Metrics.csv"


def _read_cluster_positions(cluster_id, path, name, source) -> list[str]:
    try:
        text = clusterio.read_remote_file(cluster_id, path, max_bytes=MAX_SUBSET_CSV_BYTES)
    except FileNotFoundError as exc:
        raise SubmissionValidationError(f"Session {name}: no {source} found at {path}.") from exc
    except clusterio.RemoteFileTooLargeError as exc:
        raise SubmissionValidationError(
            f"Session {name}: the {source} at {path} is larger than {MAX_SUBSET_CSV_MB} MB."
        ) from exc
    except Exception as exc:
        logger.exception("Couldn't read %s for session %r at %r on %r.", source, name, path, cluster_id)
        raise SubmissionValidationError(f"Session {name}: couldn't read the {source} at {path}.") from exc
    return positions_from_csv_text(text)


def resolve_custom_positions(session, cluster_id=None) -> list[str]:
    """Positions present in both the typed cluster CSV and the session's AreTomo metrics. Owns the
    exclusivity and path-shape checks so submit and the config builder validate one way."""
    name = session.msi_session.name
    if session.subset_selection is not None:
        raise SubmissionValidationError(
            f"Session {name} has both an uploaded subset and a cluster CSV path - keep only one."
        )
    path = session.subset_csv_path.strip()
    ensure_safe_subset_csv_path(path)
    cluster_id = cluster_id or deposition_cluster_id()
    requested = list(dict.fromkeys(_read_cluster_positions(cluster_id, path, name, "subset CSV")))
    available = set(_read_cluster_positions(cluster_id, _aretomo_metrics_path(session), name, "tilt series metrics"))
    positions = [position for position in requested if position in available]
    if not positions:
        raise SubmissionValidationError(f"Session {name}: none of the positions in {path} are in this AreTomo run.")
    return positions
