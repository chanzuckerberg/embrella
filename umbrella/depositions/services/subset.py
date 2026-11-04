"""Resolve a session's stored custom subset into the positions to keep.
At submit the prep job prunes ``{session}_TiltSeries_Metrics.csv`` to these
positions so ``cryoetportalprep sync`` processes only the selected runs.
"""


def selected_positions(subset_selection) -> list[str]:
    """The tilt-series positions to keep, or [] when there's no usable subset."""
    if not subset_selection:
        return []
    if isinstance(subset_selection, dict):
        return [_norm(v) for v in subset_selection.get("Selected positions") or [] if v]
    if isinstance(subset_selection, list):
        return [
            _norm(row["Tilt_Series"]) for row in subset_selection if isinstance(row, dict) and row.get("Tilt_Series")
        ]
    return []


def _norm(value) -> str:
    """Normalize a position to match the metrics CSV's Tilt_Series values."""
    return str(value).strip().removesuffix(".mrc")
