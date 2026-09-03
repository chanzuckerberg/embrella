"""Sort keys shared across apps: natural ("human") order, and the MSI session naming scheme."""

import re

_DIGIT_RUN = re.compile(r"(\d+)")

# Chunk kinds keep every comparison same-typed: ints sort before text at equal depth,
# and the missing sentinel sorts after everything.
_INT, _TEXT, _MISSING = 0, 1, 2
_MISSING_LAST = ((_MISSING, ""),)


def natural_sort_key(value):
    """Type-stable natural-sort key: digit runs compare numerically, text lexically.

    'pt712_ts_001' -> ((_TEXT,'pt'), (_INT,712), (_TEXT,'_ts_'), (_INT,1)), so
    'Position_2' < 'Position_10' and mixed naming shapes never raise. None and the
    string 'None' sort last.
    """
    if value is None or value == "None":
        return _MISSING_LAST

    return tuple(
        (_INT, int(chunk)) if chunk.isdigit() else (_TEXT, chunk) for chunk in _DIGIT_RUN.split(str(value)) if chunk
    )


# The MSI session naming scheme
#
#   s26sep01a
#   ^ ^^^^^^^^
#   | |      `- seq: a, b, c... n-th session that day
#   | `-------- yymmmdd
#   `---------- prefix: per SessionPlan, tells scopes/software apart (may be empty)
NAME_PREFIX_RE = re.compile(r"^[a-z]*$")
SESSION_NAME_RE = re.compile(r"^(?P<prefix>[a-z]*)(?P<yy>\d{2})(?P<mon>[a-z]{3})(?P<dd>\d{2})(?P<seq>[a-z]*)$")
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")

DEFAULT_SEQ = "a"
# Sorts after every real date (years are negated) and after every real seq letter.
UNPARSEABLE_KEY = (0, 0, 0, "z")


def msi_session_sort_key(name):
    """Newest first by the date part; the prefix only breaks ties.

    s26sep01a lands next to 26sep01a, not in a separate block. Names that don't fit the scheme
    sort last, among themselves by name.
    """
    match = SESSION_NAME_RE.match(name or "")
    if not match or match["mon"] not in MONTHS:
        return (*UNPARSEABLE_KEY, name or "")

    day = int(match["dd"])
    if not 1 <= day <= 31:
        return (*UNPARSEABLE_KEY, name or "")

    month = MONTHS.index(match["mon"]) + 1
    return (-int(match["yy"]), -month, -day, match["seq"] or DEFAULT_SEQ, match["prefix"])
