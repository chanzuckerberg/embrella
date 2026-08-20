"""Questions you can ask of a template, answered from `vocabulary`."""

import difflib
import re

from .vocabulary import FILE_SCOPED, PLACEHOLDERS, SESSION_SCOPED

# Matches `{token}`
_TOKEN_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

_BY_NAME = {p.name: p for p in PLACEHOLDERS}


def known_placeholders():
    """Every legal token name."""
    return frozenset(_BY_NAME)


def session_scoped_placeholders():
    """Token names a replacement map supplies -- legal in a directory template."""
    return frozenset(name for name, p in _BY_NAME.items() if p.scope == SESSION_SCOPED)


def file_scoped_placeholders():
    """Token names that are per-file, so they belong in a `FilePattern` capture group."""
    return frozenset(name for name, p in _BY_NAME.items() if p.scope == FILE_SCOPED)


def placeholders_in(template):
    """Every `{token}` name present in `template`, whether or not it is known.

    Use this for the fully-resolved assertion -- a resolved directory must contain zero
    placeholders, and `unknown_placeholders` would not catch a *known* file-scoped token
    surviving substitution.
    """
    return frozenset(_TOKEN_RE.findall(template or ""))


def unknown_placeholders(template):
    """Token names in `template` that nothing can substitute or capture.

    This is the typo detector: `{scop}` is indistinguishable from a legitimate token at
    substitution time, and silently survives into the stored path.
    """
    return placeholders_in(template) - known_placeholders()


def misplaced_placeholders(template):
    """File-scoped token names found in `template`, read as a *directory* template.

    A directory template must be fully substitutable at session-create time, so a
    file-scoped token in one is what leaves `{run}_{sequence}_{tilt}` in the database.
    Review templates name one exact file rather than a directory, so this does not
    apply to them.
    """
    return placeholders_in(template) & file_scoped_placeholders()


def suggest_placeholder(name):
    """Best-guess correction for an unrecognised token, or None.

    Feeds the validator's "Did you mean {scope}?" -- typos are the actual failure mode.
    """
    matches = difflib.get_close_matches(name, sorted(known_placeholders()), n=1, cutoff=0.7)
    return matches[0] if matches else None
