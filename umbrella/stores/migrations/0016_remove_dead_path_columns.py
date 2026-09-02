"""Drop the two vestigial "logical path" columns.

DESTRUCTIVE AND IRREVERSIBLE -- the reverse re-adds empty columns, it cannot recover the
strings. Snapshot before running this in production.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0015_rename_staticpath_to_datakind"),
    ]

    operations = [
        migrations.RemoveField(model_name="datakind", name="static_path"),
        migrations.RemoveField(model_name="path", name="static_path"),
    ]
