"""
Run-name allocation.

A processing run lives at ``{processing_base}/{session}/runNNN``. The next name is
one past the highest number taken, counting both the session's ProcRuns for the plan
and any directories already on disk (e.g. created outside Embrella), so a new run
never lands in an existing directory.
"""

import re
import shlex
from typing import Iterable, Optional

from django.db import transaction
from processes.models import ProcRun
from tem.models import MsiSession

from common import clusterio

RUN_NAME_RE = re.compile(r"run(\d+)")


def run_number(name: str) -> Optional[int]:
    """The number in a ``runNNN`` name, or None for anything else (``run002_old``, ``copick``)."""
    match = RUN_NAME_RE.fullmatch(name or "")
    return int(match.group(1)) if match else None


def next_run_name_from(names: Iterable[str]) -> str:
    """One past the highest ``runNNN`` in `names`, zero-padded to at least 3 digits."""
    numbers = [number for number in map(run_number, names) if number is not None]
    return f"run{max(numbers, default=0) + 1:03d}"


def _db_run_names(msi_session, proc_plan) -> list[str]:
    return list(ProcRun.objects.filter(msi_session=msi_session, proc_plan=proc_plan).values_list("name", flat=True))


def next_run_name(msi_session, proc_plan, existing_dirs: Iterable[str] = ()) -> str:
    """
    The next free run name for a session's plan.

    Args:
        msi_session: The session the run belongs to
        proc_plan: The plan the run hangs off
        existing_dirs: Run directory names already on disk (see list_run_dirs)

    Returns:
        e.g. "run004" when run001-run003 exist; "run1000" past run999
    """
    return next_run_name_from([*_db_run_names(msi_session, proc_plan), *existing_dirs])


def reserve_run(msi_session, proc_plan, existing_dirs: Iterable[str] = ()) -> ProcRun:
    """
    Create the ProcRun for the next free run name.

    The session row is locked for the transaction so concurrent reservations on the
    same session take turns instead of computing the same name. select_for_update is
    a no-op on SQLite. List the disk before calling: SSH must not run under the lock.
    """
    existing_dirs = list(existing_dirs)
    with transaction.atomic():
        MsiSession.objects.select_for_update().get(pk=msi_session.pk)
        name = next_run_name(msi_session, proc_plan, existing_dirs)
        return ProcRun.objects.create(name=name, proc_plan=proc_plan, msi_session=msi_session)


def list_run_dirs(processing_base: str, session_name: str, cluster_id: str) -> list[str]:
    """
    Names of the ``run*`` entries under ``{processing_base}/{session_name}`` on the cluster.

    Listed over SSH as the service account. A missing session directory yields [];
    connection errors propagate, so "could not look" is never mistaken for "no runs".
    """
    session_dir = f"{processing_base.rstrip('/')}/{session_name}"
    ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id)
    try:
        _, stdout, _ = ssh.exec_command(f"ls -1d {shlex.quote(session_dir)}/run* 2>/dev/null", timeout=20)
        out = stdout.read().decode("utf-8", "replace")
        return [line.strip().rstrip("/").rsplit("/", 1)[-1] for line in out.splitlines() if line.strip()]
    finally:
        ssh.close()
