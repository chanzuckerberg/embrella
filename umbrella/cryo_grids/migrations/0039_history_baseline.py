"""
Snapshot every pre-existing grid / grid label / label / container into its history table.

Without a baseline, an object's first post-install change has nothing to diff
against, e.g. a box move would show "moved to puck B" with no "from".
Rows are tagged ``baseline`` so the timeline renders them as the object's
creation (at its own creation timestamp) rather than as an install-time event.
"""

from django.db import migrations
from django.utils import timezone

BASELINE = "baseline"  # Mirrors cryo_grids.history.ChangeReason.BASELINE (migrations stay frozen)
CREATED = "+"
BATCH_SIZE = 500

TRACKED = ["CryoGrid", "GridLabel", "Label", "CryoGridBox", "Puck", "Cane", "Dewar"]


def snapshot(apps, schema_editor):
    now = timezone.now()

    for name in TRACKED:
        model = apps.get_model("cryo_grids", name)
        historical = apps.get_model("cryo_grids", f"Historical{name}")

        # Tracked columns = historical columns minus simple-history bookkeeping
        attnames = [f.attname for f in historical._meta.concrete_fields if not f.name.startswith("history_")]

        # Skip objects that already have history (e.g. touched before this migration ran)
        seen = set(historical.objects.values_list("id", flat=True).distinct())
        rows = [
            historical(**values, history_date=now, history_type=CREATED, history_change_reason=BASELINE)
            for values in model.objects.values(*attnames).iterator()
            if values["id"] not in seen
        ]

        historical.objects.bulk_create(rows, batch_size=BATCH_SIZE)


def unsnapshot(apps, schema_editor):
    for name in TRACKED:
        apps.get_model("cryo_grids", f"Historical{name}").objects.filter(history_change_reason=BASELINE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cryo_grids", "0038_label_history"),
    ]

    operations = [
        migrations.RunPython(snapshot, unsnapshot),
    ]
