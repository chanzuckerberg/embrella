from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("depositions", "0013_deposition_metadata_dataset"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="datasetjob",
            name="staged_at",
        ),
    ]
