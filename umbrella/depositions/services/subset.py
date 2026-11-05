"""Resolve a session's stored custom subset into positions for the prep config."""


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
