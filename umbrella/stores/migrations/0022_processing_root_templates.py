"""Seed the processing_root / script_dir templates the processors resolve against.

Replaces the deleted ProcSoftware.processing_directory / script_directory scalars
(processes/0045): one template row serves every software, with {proc_software}
substituting ProcSoftware.dirname (storage_dirname or name). A software whose directories
don't follow this layout overrides per-row via ProcSoftware.processing_root / script_dir.

One tree serves every scope here -- {scope} is a legal token if an install wants
per-scope roots. These are the shipped defaults; get_or_create leaves operator edits
alone.
TODO: Eventually this should read from deployment config rather than carrying CZII's
layout as the default
"""

from django.db import migrations

TEMPLATES = {
    "processing_root": "/hpc/projects/group.czii/krios1.processing/{proc_software}",
    "script_dir": "/hpc/projects/group.czii/krios1.processing/{proc_software}/scripts",
}


def forward(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    for data_type, overlay_path in TEMPLATES.items():
        kind, _ = DataKind.objects.get_or_create(data_type=data_type)
        PathType.objects.get_or_create(data_kind=kind, cluster=None, overlay_path=overlay_path)


def reverse(apps, schema_editor):
    DataKind = apps.get_model("stores", "DataKind")
    PathType = apps.get_model("stores", "PathType")
    PathType.objects.filter(data_kind__data_type__in=TEMPLATES, overlay_path__in=TEMPLATES.values()).delete()
    DataKind.objects.filter(data_type__in=TEMPLATES, pathtype__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0021_review_tokens_and_rec_pattern"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
