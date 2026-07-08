from django.db import migrations

SEED_FLAGS = [
    ("copick-web", False, "Copick-web viewer."),
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
        ("accounts", "0005_seed_feature_flags"),
    ]

    operations = [
        migrations.RunPython(seed_flags, unseed_flags),
    ]
