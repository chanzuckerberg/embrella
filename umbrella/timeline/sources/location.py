"""
Container moves → grid MOVED entries.

A box / puck / cane / dewar moving changes where its grids are without
writing any grid row. Walk up the storage chain, keeping only moves made
while the grid was inside that container:

    grid ──in──▶ box ──in──▶ puck ──in──▶ cane ──in──▶ dewar ──at──▶ site
         stays       stays        stays        stays

    e.g. grid in BoxA Jan 1 2024 → Feb 3 2026, BoxA moved to Puck2 on Jun 20 2025
         → "Box moved: Puck1 slot 1 to Puck2 slot 3"   (Jun 20 2025, kept)
         BoxA moved again on Mar 1 2026                (dropped: grid had left)
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from cryo_grids.history import LOCATION_FIELDS, ChangeReason
from cryo_grids.models import Cane, CryoGrid, CryoGridBox, Dewar, Puck

from timeline.sources.base import (
    CHANGED,
    DELETED,
    POSITION,
    SLOT,
    Spot,
    attname,
    changes,
    history,
    is_baseline,
    move_summary,
    names,
    spot_text,
    username,
)
from timeline.types import Entry, EntryKind, Subject

# Baseline snapshots predate history: the state held since "forever"
BEGINNING = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class Level:
    model: type
    via: str  # Shown to users: "Box moved: …"
    parent: str  # Container kind it sits in: "… same puck, slot 1 to 5"
    unit: str = POSITION  # What the parent's places are called: boxes sit in puck slots

    @property
    def parent_field(self) -> str:
        return attname(self.model, LOCATION_FIELDS[self.model][0])

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(attname(self.model, name) for name in LOCATION_FIELDS[self.model])

    @property
    def parent_model(self) -> type:
        return self.model._meta.get_field(LOCATION_FIELDS[self.model][0]).related_model


# Bottom-up storage chain. A new container level is one more row.
CHAIN = [
    Level(CryoGridBox, "box", "puck", SLOT),
    Level(Puck, "puck", "cane"),
    Level(Cane, "cane", "dewar", SLOT),
    Level(Dewar, "dewar", "site"),
]


@dataclass(frozen=True)
class Stay:
    """``parent_id`` held the child from ``start`` until ``end`` (None = still there)."""

    parent_id: int
    start: datetime
    end: datetime | None = None

    def holds(self, at: datetime) -> bool:
        return self.start < at and (self.end is None or at < self.end)


def stays(rows: list, parent_field: str) -> list[Stay]:
    """
    Turn one object's history rows (oldest first) into the parents it sat in.

    e.g. box_id A @Jan 1 2024, A @Jan 5 2024 (edit), B @Feb 3 2026
         → [Stay(A, Jan 1 2024, Feb 3 2026), Stay(B, Feb 3 2026)]
    """
    out: list[Stay] = []

    for row in rows:
        parent = None if row.history_type == DELETED else getattr(row, parent_field)
        current = out[-1] if out and out[-1].end is None else None

        if current and current.parent_id == parent:
            continue

        if current:
            out[-1] = replace(current, end=row.history_date)

        if parent is not None:
            start = BEGINNING if is_baseline(row) else row.history_date
            out.append(Stay(parent, start))

    return out


def clip(inner: list[Stay], outer: Stay) -> list[Stay]:
    """Restrict ``inner`` stays to the ``outer`` window (the child's own stay)."""
    out = []

    for stay in inner:
        start = max(stay.start, outer.start)
        ends = [e for e in (stay.end, outer.end) if e is not None]
        end = min(ends) if ends else None

        if end is None or start < end:
            out.append(Stay(stay.parent_id, start, end))

    return out


def moves_in(rows: list, window: Stay, level: Level) -> list:
    """``(prev, row)`` pairs where the container's location changed inside ``window``."""
    out = []
    prev = None

    for row in rows:
        moved = row.history_type == CHANGED and (
            any(name in changes(prev, row) for name in level.fields)
            or (prev is None and row.history_change_reason == ChangeReason.MOVED)
        )

        if moved and window.holds(row.history_date):
            out.append((prev, row))

        prev = row

    return out


def container_moves(grid_id: int, grid_rows: list) -> list[Entry]:
    """MOVED entries for every container move while the grid was inside it."""
    windows = stays(grid_rows, attname(CryoGrid, LOCATION_FIELDS[CryoGrid][0]))
    entries = []
    cache = {}

    for level in CHAIN:
        next_windows = []
        found = []

        for window in windows:
            key = (level.model, window.parent_id)
            if key not in cache:
                cache[key] = history(level.model, id=window.parent_id)

            rows = cache[key]
            found += moves_in(rows, window, level)
            next_windows += clip(stays(rows, level.parent_field), window)

        entries += _move_entries(grid_id, level, found)
        windows = next_windows

    return entries


def _move_entries(grid_id: int, level: Level, found: list) -> list[Entry]:
    parents = names(level.parent_model, {getattr(r, level.parent_field) for pair in found for r in pair if r})
    entries = []

    for prev, row in found:
        origin = _spot(prev, level, parents) if prev else None
        target = _spot(row, level, parents)
        detail = {
            "via": level.via,
            "container": row.name,
            "from": spot_text(origin, level.parent, level.unit) if origin else None,
            "to": spot_text(target, level.parent, level.unit),
            "reason": row.history_change_reason,
        }

        entries.append(
            Entry(
                at=row.history_date,
                subject=Subject.GRID,
                subject_id=grid_id,
                kind=EntryKind.MOVED,
                summary=move_summary(level.via.capitalize(), level.parent, origin, target, level.unit),
                user=username(row.history_user),
                detail=detail,
            )
        )

    return entries


def _spot(row, level: Level, parents: dict) -> Spot:
    parent_id, *position = (getattr(row, name) for name in level.fields)
    return Spot(parent_id, parents.get(parent_id, f"{level.parent} {parent_id}"), position[0] if position else None)
