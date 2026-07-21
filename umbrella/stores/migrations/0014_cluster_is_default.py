from django.db import migrations, models


class Migration(migrations.Migration):
    # Schema-only: adds the is_default flag. No row is marked default here — the default
    # cluster is set manually (admin / dump) so upgrades don't silently pick one.
    dependencies = [
        ("stores", "0013_proc_url_pathtype"),
    ]

    operations = [
        migrations.AddField(
            model_name="cluster",
            name="is_default",
            field=models.BooleanField(
                default=False,
                help_text="Fallback cluster for records with no explicit cluster (file URLs, review resolution).",
            ),
        ),
    ]
