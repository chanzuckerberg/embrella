"""thumb_url names its software with {proc_software}, like proc_url and zarr_url.

The row spelled `aretomo3/` since stores/0011, so a caller could not say whose thumbnails
it wanted. The respelled segment matches the seeded row (`krios1.processing/aretomo3/…`)
and the flattened demo row (`{http_base}aretomo3/…`) alike.
"""

from django.db import migrations

DATA_TYPE = "thumb_url"
OLD_SEGMENT = "aretomo3/{msi_session}/"
NEW_SEGMENT = "{proc_software}/{msi_session}/"


def _respell(apps, old, new):
    PathType = apps.get_model("stores", "PathType")
    for path_type in PathType.objects.filter(data_kind__data_type=DATA_TYPE):
        overlay = path_type.overlay_path.replace(old, new)
        if overlay != path_type.overlay_path:
            path_type.overlay_path = overlay
            path_type.save(update_fields=["overlay_path"])


def forward(apps, schema_editor):
    _respell(apps, OLD_SEGMENT, NEW_SEGMENT)


def reverse(apps, schema_editor):
    _respell(apps, NEW_SEGMENT, OLD_SEGMENT)


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0025_dataportal_env_pathtype"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
