"""Cluster id lookup helpers.

`PipeExecution.parameters['cluster_id']` is the canonical source of truth for
which cluster a run executed on — written by `workflow.execution.PipeExecutor`
at submission time. These helpers read it consistently with a shared default.

- `cluster_id_from_parameters(dict)` — read the key out of a parameters dict
  directly. Used by the SLURM syncer and job tracker which already hold a
  PipeExecution in hand.
- `cluster_id_for_run(session_name, run_number)` — look up the most recent
  PipeExecution for a (session, run) and return its cluster_id. Used by the
  metadata views and Review creation which don't have a PipeExecution yet.
- `get_default_cluster_id()` — the shared fallback, resolved from
  stores.Cluster.get_default() and cached per-process.
  Raises NoDefaultClusterError when none is set.
"""

from functools import lru_cache


class NoDefaultClusterError(RuntimeError):
    """Raised when a default cluster is needed but none is configured."""


@lru_cache(maxsize=1)
def _cached_default_cluster_id():
    """Resolve and cache the default cluster id (or None). Cleared by clear_default_cluster_cache()."""
    from stores.models import Cluster

    default = Cluster.get_default()
    return default.cluster_id if default is not None else None


def clear_default_cluster_cache(*args, **kwargs):
    """Invalidate the cached default cluster id. Wired up by connect_cache_invalidation()."""
    _cached_default_cluster_id.cache_clear()


def connect_cache_invalidation():
    """Drop the cached default-cluster id whenever any Cluster row changes.

    The id is cached per-process (see `_cached_default_cluster_id`), so a change
    to which Cluster is default would otherwise go unnoticed until restart. Call
    this once at startup from ProcessesConfig.ready().
    """
    from django.db.models.signals import post_delete, post_save
    from stores.models import Cluster

    uid = "processes.clear_default_cluster_cache"
    post_save.connect(clear_default_cluster_cache, sender=Cluster, dispatch_uid=uid)
    post_delete.connect(clear_default_cluster_cache, sender=Cluster, dispatch_uid=uid)


def get_default_cluster_id() -> str:
    """Return the id of the default cluster (cached).

    Raises NoDefaultClusterError if no default cluster is configured — callers
    should not silently proceed without a cluster.
    """
    cluster_id = _cached_default_cluster_id()
    if cluster_id is None:
        raise NoDefaultClusterError(
            "No default cluster is configured. Set one in the admin (Stores → Clusters → is_default)."
        )
    return cluster_id


def cluster_id_from_parameters(parameters, default: str = None) -> str:
    """Return parameters['cluster_id'] if present and truthy, else `default`."""
    if isinstance(parameters, dict) and parameters.get("cluster_id"):
        return parameters["cluster_id"]
    return default if default is not None else get_default_cluster_id()


def cluster_id_for_run(session_name: str, run_number: str, default: str = None) -> str:
    """Return cluster_id for the most recent PipeExecution on this session+run.

    Walks the 10 most recent PipeExecutions and returns the first non-empty
    cluster_id found in their parameters. Falls back to `default` for runs
    submitted before cluster_id was persisted.
    """
    from processes.models import PipeExecution

    qs = (
        PipeExecution.objects.filter(
            proc_run__msi_session__name=session_name,
            proc_run__name=run_number,
        )
        .order_by("-updated_at")
        .values_list("parameters", flat=True)[:10]
    )
    for params in qs:
        cid = cluster_id_from_parameters(params, default="")
        if cid:
            return cid
    return default if default is not None else get_default_cluster_id()
