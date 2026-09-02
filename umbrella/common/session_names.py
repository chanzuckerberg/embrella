"""The MSI session naming scheme, shared across apps.

s26sep01a
^ ^^^^^^^^
| |      `- seq: a, b, c... n-th session that day
| `-------- yymmmdd
`---------- prefix: per SessionPlan, tells scopes/software apart (may be empty)
"""

import re

NAME_PREFIX_RE = re.compile(r"^[a-z]*$")
