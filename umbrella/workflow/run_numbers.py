"""
Run-name allocation.

A processing run lives at ``{processing_base}/{session}/runNNN``. The next name is
one past the highest number taken, counting the session's ProcRuns for the plan and
its other runs of the same software (see list_run_dirs). The DB is the truth:
directories created on the cluster outside Embrella are ignored.
"""

import re
from typing import Iterable, Optional

from django.db import transaction
from processes.models import ProcRun, ProcSoftware
from tem.models import MsiSession

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
        existing_dirs: Other run names of the software in the session (see list_run_dirs)

    Returns:
        e.g. "run004" when run001-run003 exist; "run1000" past run999
    """
    return next_run_name_from([*_db_run_names(msi_session, proc_plan), *existing_dirs])


def reserve_run(msi_session, proc_plan, existing_dirs: Iterable[str] = ()) -> ProcRun:
    """
    Create the ProcRun for the next free run name.

    The session row is locked for the transaction so concurrent reservations on the
    same session take turns instead of computing the same name. select_for_update is
    a no-op on SQLite.
    """
    existing_dirs = list(existing_dirs)
    with transaction.atomic():
        MsiSession.objects.select_for_update().get(pk=msi_session.pk)
        name = next_run_name(msi_session, proc_plan, existing_dirs)
        return ProcRun.objects.create(name=name, proc_plan=proc_plan, msi_session=msi_session)


def list_run_dirs(softwares, msi_session) -> list[str]:
    """Run names of `msi_session` under any plan using one of `softwares` (they share directories)."""
    runs = ProcRun.objects.filter(msi_session=msi_session, proc_plan__pipeinplan__pipe__software__in=softwares)
    return list(runs.values_list("name", flat=True).distinct())


def plan_softwares(proc_plan) -> list:
    """Every software the plan chains: a run name must be free under each one's directory."""
    return list(ProcSoftware.objects.filter(pipe__pipeinplan__plan=proc_plan).distinct())


def software_run_names(softwares, session_names: Iterable[str]) -> dict[str, list[str]]:
    """
    Run names per session under any plan using one of `softwares`; list_run_dirs for many sessions.

    Returns:
        e.g. {"24nov10": ["run001", "run002"]}
    """
    runs = ProcRun.objects.filter(
        msi_session__name__in=list(session_names), proc_plan__pipeinplan__pipe__software__in=softwares
    )
    names: dict[str, list[str]] = {}
    for session_name, run_name in runs.values_list("msi_session__name", "name").distinct():
        names.setdefault(session_name, []).append(run_name)

    return names
