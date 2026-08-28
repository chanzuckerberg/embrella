"""End the zarr_url template at the directory; the filename comes from the row.

The syncer now records the discovered file path on ReviewTomogram.file_path
(processes/0046-0047), so display replays what discovery found instead of re-rendering
the {vol_suffix}/{position}_Vol.zarr convention -- which new software/scopes won't follow.
The zarrPath callers append tomogram.file_path to the resolved directory.
"""

from django.db import migrations

OLD_TAIL = "{proc_run}/{vol_suffix}/{position}_Vol.zarr"
NEW_TAIL = "{proc_run}/"


def _swap_tail(apps, old, new):
    PathType = apps.get_model("stores", "PathType")
    for path_type in PathType.objects.filter(data_kind__data_type="zarr_url"):
        if not path_type.overlay_path.endswith(old):
            continue
        path_type.overlay_path = path_type.overlay_path[: len(path_type.overlay_path) - len(old)] + new
        path_type.save(update_fields=["overlay_path"])


def forward(apps, schema_editor):
    _swap_tail(apps, OLD_TAIL, NEW_TAIL)


def reverse(apps, schema_editor):
    _swap_tail(apps, NEW_TAIL, OLD_TAIL)


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0023_constant_processing_tree"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
