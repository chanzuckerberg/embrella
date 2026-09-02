"""Rename StaticPath -> DataKind and PathType.static_path -> PathType.data_kind.

Hand-written rather than autodetected: `makemigrations` cannot infer a rename without
the interactive prompt, and would otherwise emit a delete + create that drops the rows.

Behaviour-neutral. RenameModel repoints the FK from PathType and the M2M through-table
for processes.Pipe.input automatically.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0014_cluster_is_default"),
        # processes/0007 builds Pipe.input as M2M(to="stores.staticpath") and only
        # depends on stores/0004, so without this the graph may order the rename first
        # and 0007 then fails with "Related model 'stores.staticpath' cannot be
        # resolved". Pin the rename to run after the last migration naming the old model.
        ("processes", "0007_pipe_alter_pipeparam_pipe_alter_runpipedata_pipe_and_more"),
    ]

    operations = [
        migrations.RenameModel(old_name="StaticPath", new_name="DataKind"),
        migrations.RenameField(model_name="pathtype", old_name="static_path", new_name="data_kind"),
    ]
