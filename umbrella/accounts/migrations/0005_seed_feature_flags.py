from django.db import migrations

# Flags mirror the frontend FEATURE_FLAG enum. example/review were previously
# hardcoded as always-on in the frontend; seed them enabled here so the DB is
# the single source of truth. The rest are seeded off so admins have a toggle.
SEED_FLAGS = [
    ("example", True, "Example feature flag."),
    ("review", True, "Tomogram review feature."),
    ("manage_data", False, "Manage data feature."),
    ("deposition", False, "Deposition feature."),
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
        ("accounts", "0004_systemfeatureflag"),
    ]

    operations = [
        migrations.RunPython(seed_flags, unseed_flags),
    ]
