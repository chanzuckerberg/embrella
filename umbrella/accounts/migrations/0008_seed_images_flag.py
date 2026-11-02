from django.db import migrations

# Seeded off: turn on per user or globally once the host has a media dir.
# Stays off on the public demo (no persistent media volume there yet).
SEED_FLAGS = [
    ("images", False, "Grid images: upload, view and annotate screenshots and exports."),
]


def seed_flags(apps, schema_editor):
    SystemFeatureFlag = apps.get_model("accounts", "SystemFeatureFlag")
    for name, enabled, description in SEED_FLAGS:
        SystemFeatureFlag.objects.get_or_create(
            name=name,
            defaults={"enabled": enabled, "description": description},
        )


def unseed_flags(apps, schema_editor):
    SystemFeatureFlag = apps.get_model("accounts", "SystemFeatureFlag")
    SystemFeatureFlag.objects.filter(name__in=[name for name, _, _ in SEED_FLAGS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_seed_demo_flag"),
    ]

    operations = [
        migrations.RunPython(seed_flags, unseed_flags),
    ]
