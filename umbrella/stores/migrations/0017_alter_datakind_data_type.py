"""Widen DataKind.data_type to 32 and drop its `choices` (inherited from StaticPath).

Adding a data kind should be a row, not a migration -- eight already alter this field.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0016_remove_dead_path_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datakind",
            name="data_type",
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
