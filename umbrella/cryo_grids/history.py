"""
Change reasons stamped on simple-history rows.

The diff says *what* changed; the reason says *which action* did it.
e.g. a grid row going to ``trashed=True, grid_box=None`` is ``trashed``
when the user trashed it, ``box_deleted`` when its box was deleted.
"""

from enum import StrEnum

from cryo_grids.models import Cane, CryoGrid, CryoGridBox, Dewar, Puck


class ChangeReason(StrEnum):
    MOVED = "moved"
    EDITED = "edited"
    TRASHED = "trashed"
    RESTORED = "restored"
    CLIPPED = "clipped"
    UNCLIPPED = "unclipped"
    BOX_DELETED = "box_deleted"
    PUCK_DELETED = "puck_deleted"
    BASELINE = "baseline"  # Snapshot of pre-existing objects


# Fields whose change means the object moved within the storage chain
LOCATION_FIELDS = {
    CryoGrid: ("grid_box", "position_in_box"),
    CryoGridBox: ("puck", "position_in_puck"),
    Puck: ("cane", "position_in_cane"),
    Cane: ("dewar", "position_in_dewar"),
    Dewar: ("site",),
}


def with_reason(obj, reason: ChangeReason):
    """Tag ``obj`` so its next save writes ``reason`` on the history row."""
    obj._change_reason = reason
    return obj


def edit_reason(obj, changes: dict) -> ChangeReason:
    """MOVED if ``changes`` (e.g. serializer.validated_data) alter a location field, else EDITED."""
    fields = LOCATION_FIELDS.get(type(obj), ())
    moved = any(name in changes and changes[name] != getattr(obj, name) for name in fields)

    return ChangeReason.MOVED if moved else ChangeReason.EDITED
