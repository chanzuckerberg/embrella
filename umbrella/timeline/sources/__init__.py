"""
Sources turn domain rows into timeline entries.

One module per subject: each reads its own tables (simple-history or live)
and returns ``list[Entry]``. ``timeline.services`` composes them.
"""
