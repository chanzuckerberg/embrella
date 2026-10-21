"""Proc runs on a grid's MSI sessions → CREATED entries (no user: ProcRun doesn't record one)."""

from processes.models import ProcRun

from timeline.types import Entry, EntryKind, Subject


def proc_run_entries(grid_id: int) -> list[Entry]:
    runs = ProcRun.objects.filter(msi_session__grid_id=grid_id).select_related("proc_plan", "msi_session")

    return [
        Entry(
            at=run.created_at,
            subject=Subject.PROC_RUN,
            subject_id=run.id,
            kind=EntryKind.CREATED,
            summary=f"Proc run {run.name} ({run.proc_plan.name}) created on {run.msi_session.name}",
        )
        for run in runs
    ]
