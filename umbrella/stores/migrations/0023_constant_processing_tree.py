"""Pin the processing tree: {scope}.processing becomes krios1.processing everywhere.

Processing paths no longer vary by scope -- every scope's jobs write under the one
krios1.processing volume, matching the constant roots stores/0022 seeded. This respells
the remaining template rows still saying {scope}.processing: the review/url lane and the
legacy per-file lane (whose stale /hpc/processing/ root is untouched -- separate issue).
Acquisition rows keep {scope}; instruments really are per-scope.
TODO: same as stores/0022 -- eventually read the tree name from deployment config.
"""

from django.db import migrations

# Every data type whose template spelled {scope}.processing: the review/url lane
# (proc_dir..copick_url) and the legacy per-file lane (tangl..ocpi).
SCOPED_DATA_TYPES = (
    "proc_dir",
    "proc_url",
    "zarr_url",
    "thumb_url",
    "copick_url",
    "tangl",
    "rawst",
    "ctf",
    "aln",
    "imod",
    "rec",
    "evn",
    "odd",
    "deno",
    "pick",
    "galr",
    "seg",
    "cpck",
    "ocpi",
)

OLD_TREE = "{scope}.processing"
NEW_TREE = "krios1.processing"


def _respell(apps, old, new):
    PathType = apps.get_model("stores", "PathType")
    for path_type in PathType.objects.filter(data_kind__data_type__in=SCOPED_DATA_TYPES):
        overlay = path_type.overlay_path.replace(old, new)
        if overlay != path_type.overlay_path:
            path_type.overlay_path = overlay
            path_type.save(update_fields=["overlay_path"])


def forward(apps, schema_editor):
    _respell(apps, OLD_TREE, NEW_TREE)


def reverse(apps, schema_editor):
    _respell(apps, NEW_TREE, OLD_TREE)


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0022_processing_root_templates"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
