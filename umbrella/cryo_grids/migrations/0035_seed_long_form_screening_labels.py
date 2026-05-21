from django.db import migrations

LONG_FORM_LABELS = [
    ("To Be Screened", "#1e88e5"),
    ("To Be Collected", "#43a047"),
    ("To Be Milled", "#fb8c00"),
]


def seed_long_form_labels(apps, schema_editor):
    Label = apps.get_model("cryo_grids", "Label")
    for name, color in LONG_FORM_LABELS:
        Label.objects.get_or_create(name=name, defaults={"color": color})


def remove_long_form_labels(apps, schema_editor):
    Label = apps.get_model("cryo_grids", "Label")
    Label.objects.filter(name__in=[name for name, _ in LONG_FORM_LABELS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cryo_grids", "0034_seed_screening_labels"),
    ]

    operations = [
        migrations.RunPython(seed_long_form_labels, remove_long_form_labels),
    ]
