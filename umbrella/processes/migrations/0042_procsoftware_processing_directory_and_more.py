"""Split the processing root out of script_directory.

get_processing_base_path() used to walk up from script_directory. Backfill the new field
with the same parent so configured rows keep resolving to the path they resolve to today.
"""

from pathlib import PurePosixPath

from django.db import migrations, models


def backfill_processing_directory(apps, schema_editor):
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    for row in ProcSoftware.objects.exclude(script_directory__isnull=True).exclude(script_directory=""):
        row.processing_directory = str(PurePosixPath(row.script_directory.rstrip("/")).parent)
        row.save(update_fields=["processing_directory"])


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0041_alter_pipe_input"),
    ]

    operations = [
        migrations.AddField(
            model_name="procsoftware",
            name="processing_directory",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Remote root this software's runs are written under, scanned by the syncers "
                    "(e.g., /hpc/projects/.../aretomo3). Stored rather than derived from "
                    "script_directory: the two need not be adjacent on every cluster."
                ),
                max_length=256,
            ),
        ),
        migrations.AlterField(
            model_name="procsoftware",
            name="script_directory",
            field=models.CharField(
                blank=True,
                help_text="Remote script directory (e.g., /hpc/projects/.../aretomo3/scripts)",
                max_length=256,
                null=True,
            ),
        ),
        migrations.RunPython(backfill_processing_directory, migrations.RunPython.noop),
    ]
