"""
Consolidate ProcSoftware rows that share a processor_class, then make the split
unrepresentable.

Migration 0029 already merged denoise/denoiset once and deleted the duplicate.
It did not hold: WorkflowConfig.ready() keyed its startup sync on `name`, so the
next boot recreated 'denoiset' as a fresh row and deactivated 'denoise' for not
appearing in the processor registry. Every pipe, run and execution stayed on the
inactive row while the active flag sat on an empty one, and execution resolved
plans without filtering on active -- so work kept landing on the dead row.

The companion fix in workflow/apps.py keys that sync on processor_class. This
migration merges the rows it already forked and adds the unique constraint that
stops it recurring. Do not apply this without that fix, or the next restart
forks the row again and the constraint turns it into an IntegrityError.
"""

from django.db import migrations, models
from django.db.models import Count


def consolidate_duplicate_software(apps, schema_editor):
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    Pipe = apps.get_model("processes", "Pipe")
    TomoPostProcessMethod = apps.get_model("processes", "TomoPostProcessMethod")

    duplicated_classes = list(
        ProcSoftware.objects.exclude(processor_class__isnull=True)
        .exclude(processor_class="")
        .values("processor_class")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
        .values_list("processor_class", flat=True)
    )

    if not duplicated_classes:
        print("✓ No duplicate processor_class rows to consolidate")
        return

    for processor_class in duplicated_classes:
        rows = list(ProcSoftware.objects.filter(processor_class=processor_class).order_by("id"))

        # Survivor is the row the startup sync targets: the one named after the
        # processor class. Newest row otherwise, so this stays deterministic for
        # whatever shape of duplication a given deployment is carrying.
        survivor = next((row for row in rows if row.name == processor_class), rows[-1])
        legacy_rows = [row for row in rows if row.pk != survivor.pk]

        # The row that owns pipes also owns the {proc_software} token that is
        # already materialized into stores.Path rows for every past run. Carry
        # its name onto the survivor so resolved data paths keep pointing at the
        # directories that actually exist on the cluster.
        donor = next((row for row in legacy_rows if Pipe.objects.filter(software=row).exists()), None)
        if donor is not None and survivor.name != donor.name:
            print(f"✓ Preserving path token '{donor.name}' on surviving row (was '{survivor.name}')")
            survivor.name = donor.name

        survivor.active = True
        survivor.save()

        for legacy in legacy_rows:
            legacy_label = f"'{legacy.name}' (id {legacy.pk})"
            moved_pipes = Pipe.objects.filter(software=legacy).update(software=survivor)

            # unique_together (name, software): drop a method the survivor
            # already carries rather than tripping the constraint.
            moved_methods = 0
            for method in TomoPostProcessMethod.objects.filter(software=legacy):
                if TomoPostProcessMethod.objects.filter(name=method.name, software=survivor).exists():
                    method.delete()
                else:
                    method.software = survivor
                    method.save()
                    moved_methods += 1

            survivor.capable_tasks.add(*legacy.capable_tasks.all())
            legacy.delete()
            print(
                f"✓ Merged {legacy_label} into '{survivor.name}' (id {survivor.pk}): "
                f"{moved_pipes} pipe(s), {moved_methods} post-process method(s)"
            )


def reverse_consolidate(apps, schema_editor):
    """
    Irreversible in substance.

    Dropping the unique constraint is handled by reversing the AlterField, but
    the merged rows cannot be split again -- which row a given pipe came from is
    not recorded anywhere. Restore from a backup if you need the old shape.
    """
    print("⚠ ProcSoftware rows were merged and cannot be split again. Restore from backup if needed.")


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0038_procplan_display_name"),
    ]

    operations = [
        migrations.RunPython(
            consolidate_duplicate_software,
            reverse_code=reverse_consolidate,
        ),
        migrations.AlterField(
            model_name="procsoftware",
            name="name",
            field=models.CharField(
                default="aretomo3",
                help_text="Filesystem token, not a display name: fills {proc_software} in stores.Path.",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="procsoftware",
            name="processor_class",
            field=models.CharField(
                blank=True,
                help_text='Processor class name (e.g., "aretomo3" maps to AreTomo3Processor)',
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]
