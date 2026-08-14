"""
Resolve preservation decisions onto storage tree leaves.

A StorageDecision covers a path prefix, so one row can speak for a whole
session. But, uses the longest matching prefix -- a run-level decision overrides its session-level parent.
"""

from django.db.models import Q

from processes.models import StorageDecision, StorageRunSummary, current_survey

#: No decision recorded
UNSET = "unset"

#: A parent whose descendants disagree. Presentation only -- never stored.
MIXED = "mixed"


def under_prefix(prefix, field="path_prefix"):
    """
    Q matching `prefix` itself or anything beneath it, on a directory boundary.

    A plain ``startswith`` would let a decision about ``.../run1`` also claim
    ``.../run10``, which is how one judgement quietly becomes several.
    """
    prefix = prefix.rstrip("/")
    return Q(**{field: prefix}) | Q(**{f"{field}__startswith": f"{prefix}/"})


def session_filter(session_names, field="path_prefix"):
    """
    Q matching decisions about a session, derived from the path.

    The session is already in the key -- a decision path is
    ``{base}/{software}/{session}[/{run}]`` -- so there is no stored session
    column to drift from it. Matched on directory boundaries so ``26mar02a``
    cannot also claim ``26mar02a-redo``.
    """
    condition = Q(pk__in=[])  # matches nothing, so an empty list yields no rows
    for name in session_names:
        clean = str(name).strip("/")
        if not clean:
            continue
        condition |= Q(**{f"{field}__endswith": f"/{clean}"}) | Q(**{f"{field}__contains": f"/{clean}/"})
    return condition


def covered_leaves(cluster, prefix):
    """
    Leaves of the cluster's current tree that a decision on `prefix` would cover.

    Used to reject a decision about a path that is not on disk: such a row is
    invisible in the UI and unclearable, so it has to fail at write time.
    """
    survey = current_survey(cluster)
    if survey is None:
        return StorageRunSummary.objects.none()
    return StorageRunSummary.objects.filter(under_prefix(prefix), survey=survey)


def decisions_for(cluster):
    """
    {path_prefix: status} for one cluster, longest-first.
    """
    rows = StorageDecision.objects.filter(cluster=cluster).values_list("path_prefix", "status")
    return sorted(rows, key=lambda row: -len(row[0]))


def effective_status(path_prefix, decisions):
    """
    (status, decided_at_prefix) for one path.

    `decided_at_prefix` is what tells the UI whether a status is the row's own or
    inherited from an ancestor -- without it a user cannot tell why a run says
    "delete", or which row to change to undo it.
    """
    for prefix, status in decisions:
        if path_prefix == prefix or path_prefix.startswith(prefix.rstrip("/") + "/"):
            return status, prefix
    return UNSET, None


def rollup_status(statuses):
    """
    One status for a parent from its children's.

    Empty or unanimous collapses to a single value; disagreement is MIXED
    """
    distinct = set(statuses)
    if not distinct:
        return UNSET
    if len(distinct) == 1:
        return distinct.pop()
    return MIXED
