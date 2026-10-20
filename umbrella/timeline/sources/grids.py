"""Grid and grid-label history → entries."""

from datetime import datetime, time

from cryo_grids.history import ChangeReason
from cryo_grids.models import LABEL_TYPO_WINDOW, CryoGrid, GridLabel, Label
from django.utils import timezone

from timeline.sources.base import (
    CREATED,
    DELETED,
    TRASHED,
    changes,
    history,
    is_baseline,
    is_move,
    username,
    with_prev,
)
from timeline.sources.location import GRID
from timeline.types import Entry, EntryKind, Subject

CLIPPED = "clipped"

# attname → readable name, e.g. "grid_cassette_id" → "grid cassette"
FIELD_NAMES = {f.attname: str(f.verbose_name) for f in CryoGrid._meta.concrete_fields}

# Reasons that name the action outright; the diff only fills in details
REASON_KINDS = {
    ChangeReason.EDITED: EntryKind.EDITED,
    ChangeReason.TRASHED: EntryKind.TRASHED,
    ChangeReason.RESTORED: EntryKind.RESTORED,
    ChangeReason.CLIPPED: EntryKind.CLIPPED,
    ChangeReason.UNCLIPPED: EntryKind.UNCLIPPED,
    ChangeReason.BOX_DELETED: EntryKind.TRASHED,
    ChangeReason.PUCK_DELETED: EntryKind.TRASHED,
}

# Why a grid was trashed when it wasn't the user's direct action
TRASH_CAUSES = {
    ChangeReason.BOX_DELETED: "box deleted",
    ChangeReason.PUCK_DELETED: "puck deleted",
}


def grid_entries(grid_id: int, rows: list) -> list[Entry]:
    """Entries for one grid's own history ``rows`` (oldest first). Moves come from ``grid_moves``."""
    entries = []

    for prev, row in with_prev(rows):
        entry = _grid_entry(grid_id, prev, row)
        if entry:
            entries.append(entry)

    return entries


def label_entries(grid_id: int) -> list[Entry]:
    """Label added / removed entries, from GridLabel history. Typo labels are left out."""
    rows = history(GridLabel, grid_id=grid_id)
    labels = _labels({r.label_id for r in rows})
    entries = []

    for row in rows:
        label = labels.get(row.label_id)
        if _is_typo(label):
            continue

        detail = {"label": label.name if label else None, "color": label.color if label else None}
        name = detail["label"] or "(unknown label)"

        if row.history_type == CREATED:
            # Baseline rows predate history: use the label's own added_at / added_by
            baseline = is_baseline(row)
            at = row.added_at if baseline else row.history_date
            user = username(row.added_by) if baseline else username(row.history_user)
            entries.append(_entry(grid_id, at, EntryKind.LABEL_ADDED, f"Label {name} added", user, detail))

        if row.history_type == DELETED:
            user = username(row.history_user)
            entries.append(
                _entry(grid_id, row.history_date, EntryKind.LABEL_REMOVED, f"Label {name} removed", user, detail)
            )

    return entries


def _labels(ids: set) -> dict:
    """``{id: label}``; deleted labels (e.g. auto-removed typos) come from their last history snapshot."""
    found = {lbl.id: lbl for lbl in Label.objects.filter(id__in=ids)}

    for row in Label.history.filter(id__in=ids - found.keys()).order_by("history_date"):
        found[row.id] = row

    return found


def _is_typo(label) -> bool:
    """Deleted within LABEL_TYPO_WINDOW of creation, i.e. auto-removed by update_labels."""
    deleted = getattr(label, "history_type", None) == DELETED
    return deleted and label.history_date - label.created_at <= LABEL_TYPO_WINDOW


def _grid_entry(grid_id, prev, row) -> Entry | None:
    user = username(row.history_user)

    if row.history_type == CREATED:
        return _created(grid_id, row)

    if row.history_type == DELETED:
        return _entry(grid_id, row.history_date, EntryKind.DELETED, "Grid deleted", user)

    if is_move(prev, row, GRID.fields):
        return None

    diff = changes(prev, row)
    reason = row.history_change_reason
    if not diff and not reason:
        return None

    kind = REASON_KINDS.get(reason) or _kind_from_diff(diff)
    detail = {"reason": reason, "changes": {name: list(values) for name, values in diff.items()}}
    summary = _summary(kind, reason, diff)

    return _entry(grid_id, row.history_date, kind, summary, user, detail)


def _created(grid_id, row) -> Entry:
    """Baseline rows predate history: show creation at the grid's own create_on, by its owner."""
    if not is_baseline(row):
        return _entry(grid_id, row.history_date, EntryKind.CREATED, "Grid created", username(row.history_user))

    at = timezone.make_aware(datetime.combine(row.create_on, time.min))
    return _entry(grid_id, at, EntryKind.CREATED, "Grid created", username(row.user))


def _kind_from_diff(diff: dict) -> EntryKind:
    """Classify rows without a reason (e.g. admin edits); moves are already filtered out by is_move."""
    if TRASHED in diff:
        return EntryKind.TRASHED if diff[TRASHED][1] else EntryKind.RESTORED

    if CLIPPED in diff:
        return EntryKind.CLIPPED if diff[CLIPPED][1] else EntryKind.UNCLIPPED

    return EntryKind.EDITED


def _summary(kind, reason, diff) -> str:
    if kind == EntryKind.TRASHED and reason in TRASH_CAUSES:
        return f"Trashed ({TRASH_CAUSES[reason]})"

    # e.g. "Edited blot time, notes"
    if kind == EntryKind.EDITED and diff:
        return f"Edited {', '.join(FIELD_NAMES.get(name, name) for name in diff)}"

    return kind.capitalize()


def _entry(grid_id, at, kind, summary, user, detail=None) -> Entry:
    return Entry(
        at=at,
        subject=Subject.GRID,
        subject_id=grid_id,
        kind=kind,
        summary=summary,
        user=user,
        detail=detail or {},
    )
