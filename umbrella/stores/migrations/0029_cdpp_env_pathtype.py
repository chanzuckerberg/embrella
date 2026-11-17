"""Seed the cdpp_env path: the conda env with the cryoet-pipeline CLI the cdpp processor runs."""

from django.db import migrations

KIND = "cdpp_env"
DEFAULT = "/hpc/projects/group.czii/conda_environments/cdpp"


def forward(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    kind, _ = DataKind.objects.get_or_create(data_type=KIND)
    PathType.objects.get_or_create(data_kind=kind, cluster=None, defaults={"overlay_path": DEFAULT})


def reverse(apps, schema_editor):
    PathType = apps.get_model("stores", "PathType")
    PathType.objects.filter(data_kind__data_type=KIND, cluster=None, overlay_path=DEFAULT).delete()


class Migration(migrations.Migration):
    dependencies = [("stores", "0028_deposition_sync_destination_pathtype")]

    operations = [migrations.RunPython(forward, reverse)]
