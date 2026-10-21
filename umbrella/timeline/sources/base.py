"""Helpers for reading simple-history tables."""

from dataclasses import dataclass

from cryo_grids.history import ChangeReason

from timeline.types import Entry, EntryKind, Subject

# simple-history ``history_type`` values
CREATED = "+"
CHANGED = "~"
DELETED = "-"


def history(model, **filters) -> list:
    """History rows of ``model`` matching ``filters``, oldest first."""
    return list(model.history.filter(**filters).select_related("history_user").order_by("history_date", "history_id"))


def with_prev(rows):
    """
    Pair each row with the previous row of the same object.

    e.g. rows for labels 1, 2, 1 → (None, r1), (None, r2), (r1, r1')
    """
    last = {}
    for row in rows:
        yield last.get(row.id), row
        last[row.id] = row


def changes(prev, row) -> dict:
    """Tracked fields that differ between two snapshots: ``{attname: (old, new)}``."""
    if prev is None:
        return {}

    pairs = ((f.attname, getattr(prev, f.attname), getattr(row, f.attname)) for f in row.tracked_fields)
    return {name: (old, new) for name, old, new in pairs if old != new}


TRASHED = "trashed"


def is_move(prev, row, fields) -> bool:
    """
    Did this row move the object? The reason decides when stamped, else the diff of location ``fields``.

    Trashing also clears the box, but it's a trash, not a move.
    """
    if row.history_type != CHANGED:
        return False

    if row.history_change_reason:
        return row.history_change_reason == ChangeReason.MOVED

    diff = changes(prev, row)
    return TRASHED not in diff and any(name in diff for name in fields)


def is_baseline(row) -> bool:
    return row.history_change_reason == ChangeReason.BASELINE


def grid_entry(grid_id: int, at, kind: EntryKind, summary: str, user: str | None, detail=None) -> Entry:
    """An entry about the grid itself, e.g. it moved, or its box did."""
    return Entry(
        at=at,
        subject=Subject.GRID,
        subject_id=grid_id,
        kind=kind,
        summary=summary,
        user=user,
        detail=detail or {},
    )


def username(user) -> str | None:
    return user.username if user else None


def attname(model, name: str) -> str:
    """e.g. ``attname(CryoGrid, "grid_box")`` → ``"grid_box_id"``."""
    return model._meta.get_field(name).attname


def latest(model, ids) -> dict:
    """
    ``{id: object}`` for ``ids``: the live object, or its last history row once deleted (if tracked).

    e.g. a typo label auto-deleted by update_labels comes back as its ``-`` history row
    """
    ids = {i for i in ids if i is not None}
    found = {obj.id: obj for obj in model.objects.filter(id__in=ids)}

    missing = ids - found.keys()
    if missing and hasattr(model, "history"):
        for row in model.history.filter(id__in=missing).order_by("history_date"):
            found[row.id] = row

    return found


def names(model, ids) -> dict:
    """``{id: name}`` for ``ids``, deleted objects included (see ``latest``)."""
    return {i: obj.name for i, obj in latest(model, ids).items()}


@dataclass(frozen=True)
class Spot:
    """Where something sat: its container (e.g. a box) and position in it."""

    container_id: int | None
    container: str
    position: int | None = None


POSITION = "position"
SLOT = "slot"


def spot_text(spot: Spot, noun: str, unit: str = POSITION) -> str:
    """e.g. ``BoxA position 2``, ``PuckA slot 3``; ``SiteA`` (no positions); ``no box`` (outside any)."""
    if spot.container_id is None:
        return f"no {noun}"

    return spot.container if spot.position is None else f"{spot.container} {unit} {spot.position}"


def move_summary(subject: str, noun: str, origin: Spot | None, target: Spot, unit: str = POSITION) -> str:
    """
    One wording for every move; ``noun`` is the container kind, ``unit`` what its places are called:

        Grid moved: same box, position 1 to 4
        Grid moved: BoxA position 1 to BoxB position 2
        Box moved: unknown puck to PuckB slot 3   (no earlier snapshot)
    """
    if origin is None:
        return f"{subject} moved: unknown {noun} to {spot_text(target, noun, unit)}"

    same = origin.container_id is not None and origin.container_id == target.container_id
    if same and origin.position is not None:
        return f"{subject} moved: same {noun}, {unit} {origin.position} to {target.position}"

    return f"{subject} moved: {spot_text(origin, noun, unit)} to {spot_text(target, noun, unit)}"
