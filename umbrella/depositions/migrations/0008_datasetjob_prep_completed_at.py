from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("depositions", "0007_datasetjob_cluster_id")]

    operations = [
        migrations.AddField(
            model_name="datasetjob",
            name="prep_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
