"""Timeline vocabulary shared by every source."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Subject(StrEnum):
    """What an entry is about, so views (grid, session browser) can link and filter."""

    GRID = "grid"
    MSI_SESSION = "msi_session"
    PROC_RUN = "proc_run"


class EntryKind(StrEnum):
    CREATED = "created"
    EDITED = "edited"
    MOVED = "moved"
    TRASHED = "trashed"
    RESTORED = "restored"
    CLIPPED = "clipped"
    UNCLIPPED = "unclipped"
    LABEL_ADDED = "label_added"
    LABEL_REMOVED = "label_removed"
    IMAGE_ADDED = "image_added"
    IMAGE_REMOVED = "image_removed"
    DELETED = "deleted"


@dataclass(frozen=True)
class Entry:
    at: datetime
    subject: Subject
    subject_id: int
    kind: EntryKind
    summary: str
    user: str | None = None
    detail: dict = field(default_factory=dict)
