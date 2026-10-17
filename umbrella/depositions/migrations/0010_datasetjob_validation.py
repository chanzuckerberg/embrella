from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("depositions", "0009_datasetjob_progress")]

    operations = [
        migrations.AddField(model_name="datasetjob", name="validation", field=models.JSONField(blank=True, null=True)),
    ]
