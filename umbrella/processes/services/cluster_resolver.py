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
"""


def _default_cluster_id() -> str:
    from workflow.constants import DEFAULT_CLUSTER_ID

    return DEFAULT_CLUSTER_ID


def cluster_id_from_parameters(parameters, default: str = None) -> str:
    """Return parameters['cluster_id'] if present and truthy, else `default`."""
    if isinstance(parameters, dict) and parameters.get("cluster_id"):
        return parameters["cluster_id"]
    return default if default is not None else _default_cluster_id()


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
    return default if default is not None else _default_cluster_id()
