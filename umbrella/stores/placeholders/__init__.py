"""The placeholder vocabulary for path templates -- the single source of truth.

Path templates carry `{token}` placeholders that
`stores.models.fill_place_holders` substitutes.

`vocabulary` declares the tokens; `analysis` answers questions about a template.
Import from this package, not the submodules.
"""

from .analysis import (
    file_scoped_placeholders,
    known_placeholders,
    misplaced_placeholders,
    placeholders_in,
    session_scoped_placeholders,
    suggest_placeholder,
    unknown_placeholders,
)
from .vocabulary import FILE_SCOPED, PLACEHOLDERS, SESSION_SCOPED, Placeholder

__all__ = [
    "FILE_SCOPED",
    "PLACEHOLDERS",
    "SESSION_SCOPED",
    "Placeholder",
    "file_scoped_placeholders",
    "known_placeholders",
    "misplaced_placeholders",
    "placeholders_in",
    "session_scoped_placeholders",
    "suggest_placeholder",
    "unknown_placeholders",
]
