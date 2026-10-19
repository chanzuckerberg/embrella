"""Compose source entries into ordered timelines."""

from cryo_grids.models import CryoGrid

from timeline.sources.base import history
from timeline.sources.grids import grid_entries, label_entries
from timeline.sources.location import container_moves
from timeline.sources.msi_sessions import msi_session_entries
from timeline.sources.proc_runs import proc_run_entries
from timeline.types import Entry


def grid_timeline(grid_id: int) -> list[Entry] | None:
    """
    Everything that happened to a grid, newest first. ``None`` if the grid never existed.

    Trashed and deleted grids keep their timeline: history rows outlive the grid.
    """
    rows = history(CryoGrid, id=grid_id)
    if not rows and not CryoGrid.objects.filter(id=grid_id).exists():
        return None

    entries = [
        *grid_entries(grid_id, rows),
        *label_entries(grid_id),
        *container_moves(grid_id, rows),
        *msi_session_entries(grid_id),
        *proc_run_entries(grid_id),
    ]

    return sorted(entries, key=lambda e: e.at, reverse=True)
