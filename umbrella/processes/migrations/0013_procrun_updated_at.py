
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0012_procrun_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="procrun",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
