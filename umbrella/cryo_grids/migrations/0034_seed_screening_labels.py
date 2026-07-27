from django.db import migrations

SCREENING_LABELS = [
    ("TBS", "#1e88e5"),
    ("TBC", "#43a047"),
    ("TBM", "#fb8c00"),
    ("Arctis", "#8e24aa"),
    ("Hydra1", "#5e35b1"),
    ("Hydra2", "#3949ab"),
    ("Krios1", "#00897b"),
    ("Krios2", "#039be5"),
    ("P1", "#e53935"),
    ("P2", "#f4511e"),
    ("P3", "#fdd835"),
]


def seed_screening_labels(apps, schema_editor):
    Label = apps.get_model("cryo_grids", "Label")
    for name, color in SCREENING_LABELS:
        Label.objects.get_or_create(name=name, defaults={"color": color})


def remove_screening_labels(apps, schema_editor):
    Label = apps.get_model("cryo_grids", "Label")
    Label.objects.filter(name__in=[name for name, _ in SCREENING_LABELS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cryo_grids", "0033_label_gridlabel_cryogrid_labels"),
    ]

    operations = [
        migrations.RunPython(seed_screening_labels, remove_screening_labels),
    ]
