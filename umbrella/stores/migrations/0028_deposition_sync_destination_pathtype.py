"""Seed a configurable S3 base for deposition prep and push."""

from django.db import migrations

KIND = "deposition_sync_destination"
DEFAULT = "s3://cryoetportal-biohub-hpc-globus/CZII"


def forward(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    kind, _ = DataKind.objects.get_or_create(data_type=KIND)
    PathType.objects.get_or_create(data_kind=kind, cluster=None, defaults={"overlay_path": DEFAULT})


def reverse(apps, schema_editor):
    PathType = apps.get_model("stores", "PathType")
    PathType.objects.filter(data_kind__data_type=KIND, cluster=None, overlay_path=DEFAULT).delete()


class Migration(migrations.Migration):
    dependencies = [("stores", "0027_deposition_staging_pathtype")]

    operations = [migrations.RunPython(forward, reverse)]
