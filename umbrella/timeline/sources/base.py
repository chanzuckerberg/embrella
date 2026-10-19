"""Helpers for reading simple-history tables."""

from cryo_grids.history import ChangeReason

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


def is_baseline(row) -> bool:
    return row.history_change_reason == ChangeReason.BASELINE


def username(user) -> str | None:
    return user.username if user else None


def attname(model, name: str) -> str:
    """e.g. ``attname(CryoGrid, "grid_box")`` → ``"grid_box_id"``."""
    return model._meta.get_field(name).attname


def names(model, ids) -> dict:
    """
    ``{id: name}`` for ``ids``.

    Falls back to the latest history snapshot for deleted objects, if tracked.
    """
    ids = {i for i in ids if i is not None}
    found = dict(model.objects.filter(id__in=ids).values_list("id", "name"))

    missing = ids - found.keys()
    if missing and hasattr(model, "history"):
        for row in model.history.filter(id__in=missing).order_by("history_date"):
            found[row.id] = row.name

    return found
