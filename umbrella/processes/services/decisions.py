"""
Resolve preservation decisions onto storage tree leaves.

A StorageDecision covers a path prefix, so one row can speak for a whole
session. But, uses the longest matching prefix -- a run-level decision overrides its session-level parent.
"""

from processes.models import StorageDecision

#: No decision recorded
UNSET = "unset"

#: A parent whose descendants disagree. Presentation only -- never stored.
MIXED = "mixed"


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
