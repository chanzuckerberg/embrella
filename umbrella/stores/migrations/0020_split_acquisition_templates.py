"""Split every acquisition template into a directory and a FilePattern.

    /hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}_{sequence}_{tilt}_*.eer
    └──────────────── directory, stays on PathType ──────────┘└──── FilePattern ─────┘

The halves vary for different reasons and are knowable at different times -- the directory
resolves when a session is created, the filename only once a file exists. Sharing one field
is why `stores.Path` held strings that were neither a path nor a glob, and why nothing
globbed them.

Only the acquisition kinds are split. A processing template names one output file whose
{run} the pipeline substitutes from real data, so it is already whole.

The regexes are derived from the filename half, so they are exactly as precise as the
template was, and no more: they have never been matched against a real listing. Paste real
basenames into a pattern's `sample_filenames` (Stores -> File patterns) to check them.
"""

import re

from django.db import migrations

# The kinds a tem.Software role FK points at. Frozen here rather than imported from
# tem.SOFTWARE_PATH_ROLES: those are roles ("mdocs"), these are data types ("mdoc").
ACQUISITION_DATA_TYPES = ("frames", "sums", "mdoc", "parents", "atlas", "satlas")

# What each file-scoped token captures, mirrored from stores/placeholders/vocabulary.py at
# the time of this migration. `run` and `run_stage_pos` are greedy because a tilt-series id
# contains underscores itself (Position_96_2), so the tighter neighbours settle the split.
CAPTURES = {
    "run": r".+",
    "run_stage_pos": r".+",
    "sequence": r"\d+",
    "tilt": r"-?\d+(?:\.\d+)?",
    "timestamp": r"[\w-]+",
    "date": r"[\d-]+",
    "position": r".+",
}
DEFAULT_CAPTURE = r".+"

# The pre-rename spelling of {atlas_session}, still in the seeded satlas row: tem/0012
# renamed the field, the seed script was fixed in 2918777f, this row never was.
STALE_TOKENS = {"{grid_session}": "{atlas_session}"}

_TOKEN = re.compile(r"\{(\w+)\}")
_TOKEN_OR_GLOB = re.compile(r"\{(\w+)\}|([*?])")
# Two globs separated only by punctuation list a superset of what one glob does, and the
# regex is the precise filter -- so collapse them, but keep literal words (_Exposure, tomo).
_ADJACENT_GLOBS = re.compile(r"\*[^A-Za-z0-9]*\*")

NOTES = "Split off an acquisition directory template. Add real basenames to check the regex."


def split_at_last_slash(template):
    """(directory ending in "/", filename half) -- design rule 1."""
    directory, _, filename = template.rpartition("/")
    return directory + "/", filename


def regex_from_filename(filename):
    """An anchored basename regex: every {token} becomes a named group, every * a wildcard."""
    parts, pos = ["^"], 0
    for found in _TOKEN_OR_GLOB.finditer(filename):
        parts.append(re.escape(filename[pos : found.start()]))
        token, glob = found.groups()
        if token:
            parts.append("(?P<%s>%s)" % (token, CAPTURES.get(token, DEFAULT_CAPTURE)))
        else:
            parts.append(".*" if glob == "*" else ".")
        pos = found.end()
    parts.append(re.escape(filename[pos:]))
    parts.append("$")
    return "".join(parts)


def glob_from_filename(filename):
    """The `ls` filter that must list a superset of what the regex accepts."""
    glob = _TOKEN.sub("*", filename)
    while True:
        collapsed = _ADJACENT_GLOBS.sub("*", glob)
        if collapsed == glob:
            return glob
        glob = collapsed


def filename_from_regex(regex):
    """The inverse of `regex_from_filename` -- what the reverse migration re-joins.

    Inverts only what that function generates, not an arbitrary regex.
    """
    body = regex.removeprefix("^").removesuffix("$")
    out, i = [], 0
    while i < len(body):
        if body.startswith("(?P<", i):
            end = _end_of_group(body, i)
            out.append("{%s}" % body[i + 4 : body.index(">", i)])
            i = end
        elif body.startswith(".*", i):
            out.append("*")
            i += 2
        elif body[i] == "\\":
            out.append(body[i + 1])
            i += 2
        elif body[i] == ".":
            out.append("?")
            i += 1
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def _end_of_group(body, start):
    """Index just past the ")" closing the group opening at `start`."""
    depth, i = 0, start
    while i < len(body):
        if body[i] == "\\":
            i += 2
            continue
        if body[i] == "(":
            depth += 1
        elif body[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced group in %r" % body)


def _acquisition_path_types(apps):
    return apps.get_model("stores", "PathType").objects.filter(data_kind__data_type__in=ACQUISITION_DATA_TYPES)


def split_templates(apps, schema_editor):
    FilePattern = apps.get_model("stores", "FilePattern")
    for path_type in _acquisition_path_types(apps).select_related("data_kind"):
        template = path_type.overlay_path
        for stale, current in STALE_TOKENS.items():
            template = template.replace(stale, current)

        directory, filename = split_at_last_slash(template)
        if not filename or "/" not in template:
            # Already a directory, or not a path at all. Only the token repair applies.
            if template != path_type.overlay_path:
                path_type.overlay_path = template
                path_type.save(update_fields=["overlay_path"])
            continue

        # The filename half is the label: self-describing in a dropdown, and it makes two
        # PathTypes with the same convention (both mdoc rows) share one pattern row.
        pattern, _ = FilePattern.objects.get_or_create(
            data_kind=path_type.data_kind,
            label=filename,
            defaults={
                "list_glob": glob_from_filename(filename),
                "regex": regex_from_filename(filename),
                "notes": NOTES,
            },
        )
        path_type.overlay_path = directory
        path_type.file_pattern = pattern
        path_type.save(update_fields=["overlay_path", "file_pattern"])


def rejoin_templates(apps, schema_editor):
    """Put the filename back on the directory and drop the patterns this created.

    Not restored: the stale {grid_session} spelling. The seeds and the vocabulary both say
    {atlas_session}, so re-inserting a token nothing substitutes would only recreate a row
    that resolves to a path with a literal brace in it.
    """
    FilePattern = apps.get_model("stores", "FilePattern")
    for path_type in _acquisition_path_types(apps).select_related("file_pattern"):
        pattern = path_type.file_pattern
        if pattern is None:
            continue
        path_type.overlay_path = path_type.overlay_path + filename_from_regex(pattern.regex)
        path_type.file_pattern = None
        path_type.save(update_fields=["overlay_path", "file_pattern"])

    FilePattern.objects.filter(notes=NOTES, path_types__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0019_filepattern_pathtype_file_pattern"),
    ]

    operations = [
        migrations.RunPython(split_templates, rejoin_templates),
    ]
