from django.db import migrations

# Seeded off: only the public demo deployment turns this on (populate_demo bakes
# enabled=True into the curated dump). get_or_create — never update_or_create —
# because the nightly reset loads that dump and runs migrate afterwards, so an
# update would switch the demo banner back off every night.
SEED_FLAGS = [
    ("demo", False, "Public demo server: no cluster access."),
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
        ("accounts", "0006_seed_copick_web_flag"),
    ]

    operations = [
        migrations.RunPython(seed_flags, unseed_flags),
    ]
