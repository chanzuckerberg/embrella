"""Natural ("human") sort keys shared across apps."""

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
