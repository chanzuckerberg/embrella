"""Seed the deposition_staging path (prep/push output_dir)."""

from django.db import migrations

KIND = "deposition_staging"
DEFAULT = "/hpc/projects/group.czii/depositions/{deposition_id}/"


def forward(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    kind, _ = DataKind.objects.get_or_create(data_type=KIND)
    PathType.objects.get_or_create(data_kind=kind, cluster=None, overlay_path=DEFAULT)


def reverse(apps, schema_editor):
    PathType = apps.get_model("stores", "PathType")
    PathType.objects.filter(data_kind__data_type=KIND, overlay_path=DEFAULT).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0026_thumb_url_proc_software"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
