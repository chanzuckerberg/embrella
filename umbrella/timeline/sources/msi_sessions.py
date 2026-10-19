"""MSI sessions on a grid → CREATED entries (sessions are never edited, so created_at is enough)."""

from tem.models import MsiSession

from timeline.sources.base import username
from timeline.types import Entry, EntryKind, Subject


def msi_session_entries(grid_id: int) -> list[Entry]:
    sessions = MsiSession.objects.filter(grid_id=grid_id).select_related("user")

    return [
        Entry(
            at=session.created_at,
            subject=Subject.MSI_SESSION,
            subject_id=session.id,
            kind=EntryKind.CREATED,
            summary=f"MSI session {session.name} created",
            user=username(session.user),
            detail={"name": session.name},
        )
        for session in sessions
    ]
