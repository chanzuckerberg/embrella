from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("depositions", "0010_datasetjob_validation")]

    operations = [
        migrations.AddField(
            model_name="deposition",
            name="metadata_config_dataset",
            field=models.ForeignKey(
                to="depositions.dataset",
                to_field="dataset_id",
                on_delete=models.SET_NULL,
                related_name="+",
                blank=True,
                null=True,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="datasetjob",
            name="ingestion_state",
            field=models.CharField(
                max_length=16,
                default="not_started",
                db_index=True,
                choices=[
                    ("not_started", "not_started"),
                    ("opening_pr", "opening_pr"),
                    ("pr_opened", "pr_opened"),
                    ("failed", "failed"),
                ],
            ),
        ),
        migrations.AddField(model_name="datasetjob", name="ingestion_pr_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="datasetjob", name="ingestion_error", field=models.TextField(blank=True)),
        migrations.AddField(
            model_name="datasetjob", name="ingestion_branch", field=models.CharField(max_length=255, blank=True)
        ),
        migrations.AddField(
            model_name="datasetjob", name="last_validated_hash", field=models.CharField(max_length=64, blank=True)
        ),
        migrations.AddField(
            model_name="datasetjob",
            name="ingestion_attempt",
            field=models.CharField(max_length=32, blank=True, editable=False),
        ),
    ]
