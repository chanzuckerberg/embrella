
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("depositions", "0014_remove_datasetjob_staged_at"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dataset",
            name="status",
        ),
    ]
