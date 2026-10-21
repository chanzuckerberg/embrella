from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("depositions", "0008_datasetjob_prep_completed_at")]

    operations = [
        migrations.AddField(model_name="datasetjob", name="sync_progress", field=models.JSONField(blank=True, null=True)),
        migrations.AddField(model_name="datasetjob", name="sync_summary", field=models.JSONField(blank=True, null=True)),
        migrations.AddField(model_name="datasetjob", name="push_progress", field=models.JSONField(blank=True, null=True)),
    ]
