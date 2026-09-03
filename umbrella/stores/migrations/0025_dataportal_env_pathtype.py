"""Seed the dataportal_env path"""

from django.db import migrations

DATAPORTAL_ENV_KIND = "dataportal_env"
DATAPORTAL_ENV_DEFAULT = "/hpc/projects/group.czii/krios1.processing/software/dataportalenv"


def forward(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    kind, _ = DataKind.objects.get_or_create(data_type=DATAPORTAL_ENV_KIND)
    PathType.objects.get_or_create(data_kind=kind, cluster=None, overlay_path=DATAPORTAL_ENV_DEFAULT)


def reverse(apps, schema_editor):
    PathType = apps.get_model("stores", "PathType")
    PathType.objects.filter(data_kind__data_type=DATAPORTAL_ENV_KIND, overlay_path=DATAPORTAL_ENV_DEFAULT).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0024_zarr_url_ends_at_directory"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
