"""Resolve a data kind to a concrete directory.

    from stores.paths import resolve_dir

    resolve_dir("copick_root", cluster=cluster, msi_session="24nov10", proc_run="run001")

To convert a constant: add a `DataKind` row, add a `PathType` row holding the directory
template, call `resolve_dir`
"""

from stores.models import PathType, fill_place_holders
from stores.placeholders import misplaced_placeholders, placeholders_in


class UnresolvedPlaceholderError(ValueError):
    """A template kept tokens after substitution, so the result is not a usable path."""


def resolve_dir(kind, *, cluster=None, strict=True, **context):
    """Return the directory `kind` resolves to, fully substituted.

    `kind`     -- DataKind.data_type, e.g. "frames", "copick_root".
    `cluster`  -- a Cluster (or cluster_id) selecting a per-cluster override of the
                  template; falls back to the cluster-agnostic row.
    `strict`   -- raise if any token survives substitution. If off, will not raise error and return tokens wrapped in {}
    `**context`-- placeholder values. Names come from `stores.placeholders`; a typo here
                  is caught by `strict`, not silently passed through.
    """
    path_type = PathType.resolve(kind, cluster=cluster)
    if path_type is None:
        where = getattr(cluster, "cluster_id", cluster)
        raise PathType.DoesNotExist(
            f"No PathType for data kind {kind!r}"
            + (f" on cluster {where!r}" if where else "")
            + ". Add one in the admin under Stores → Path types."
        )

    resolved = fill_place_holders(path_type.overlay_path, context)
    if strict:
        assert_fully_resolved(resolved, describe=f"PathType {path_type.pk} for {kind!r}")
    return resolved


def assert_fully_resolved(resolved, *, describe):
    """Raise unless every `{token}` in `resolved` was substituted.

    The one acceptance criterion of the whole split: a stored path is a directory, not a
    half-filled template. `describe` names what was being resolved, for the message.
    """
    leftover = placeholders_in(resolved)
    if not leftover:
        return
    misplaced = misplaced_placeholders(resolved)
    if misplaced:
        raise UnresolvedPlaceholderError(
            f"{describe} is a directory template but names file-scoped token(s) "
            f"{_fmt(misplaced)}. Those identify a file within the directory and belong in "
            f"a FilePattern capture group, not here."
        )
    raise UnresolvedPlaceholderError(
        f"{describe} resolved to {resolved!r}, which still contains {_fmt(leftover)}. Supply the missing value(s)."
    )


def _fmt(names):
    return ", ".join("{%s}" % n for n in sorted(names))
