"""
Guarantee exactly one placeholder grid ("default grid") per instance.

    existing instance: flag the grid already named "default grid" (id and sessions unchanged)
    fresh instance:    create it, bare (no freezing session, specimen or owner)
"""

from django.db import migrations

PLACEHOLDER_NAME = "default grid"
PLACEHOLDER_NOTES = "This is a default grid when no corresponding grid information is available in the database."


def seed_placeholder(apps, schema_editor):
    CryoGrid = apps.get_model("cryo_grids", "CryoGrid")
    if CryoGrid.objects.filter(is_placeholder=True).exists():
        return

    # Oldest match, trashed or not: there is only ever one placeholder
    existing = CryoGrid.objects.filter(name__iexact=PLACEHOLDER_NAME).order_by("id").first()
    if existing:
        CryoGrid.objects.filter(pk=existing.pk).update(is_placeholder=True)
        return

    CryoGrid.objects.create(name=PLACEHOLDER_NAME, notes=PLACEHOLDER_NOTES, is_placeholder=True)


class Migration(migrations.Migration):
    dependencies = [
        ("cryo_grids", "0043_cryogrid_is_placeholder"),
    ]

    # Reverse is a no-op: sessions PROTECT the grid, and dropping the field undoes the flag
    operations = [
        migrations.RunPython(seed_placeholder, migrations.RunPython.noop),
    ]
