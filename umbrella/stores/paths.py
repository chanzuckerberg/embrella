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
        _assert_fully_resolved(kind, path_type, resolved)
    return resolved


def _assert_fully_resolved(kind, path_type, resolved):
    leftover = placeholders_in(resolved)
    if not leftover:
        return
    # A file-scoped token here means the template still carries its filename half; that is
    # a different mistake from a missing context value, so say which one it is.
    misplaced = misplaced_placeholders(path_type.overlay_path)
    if misplaced:
        raise UnresolvedPlaceholderError(
            f"PathType {path_type.pk} for {kind!r} is a directory template but names "
            f"file-scoped token(s) {_fmt(misplaced)}. Those identify a file within the "
            f"directory and belong in a FilePattern capture group, not here."
        )
    raise UnresolvedPlaceholderError(
        f"{kind!r} resolved to {resolved!r}, which still contains {_fmt(leftover)}. "
        f"Pass the missing value(s) to resolve_dir()."
    )


def _fmt(names):
    return ", ".join("{%s}" % n for n in sorted(names))
