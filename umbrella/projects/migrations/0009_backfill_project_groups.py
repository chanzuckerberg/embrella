"""Create role groups for existing projects; make each leader an EDITOR.

Mirrors projects.services (ensure_groups, ensure_leader, sync_groups) with
historical models, since migrations can't import live code safely.
"""

from django.db import migrations

GROUP_NAME = "project:{id}:{role}"
VIEWER = "viewer"
EDITOR = "editor"


def backfill(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    ProjectMembership = apps.get_model("projects", "ProjectMembership")
    Group = apps.get_model("auth", "Group")
    UserGroup = apps.get_model("auth", "User").groups.through

    for project in Project.objects.all():
        # Role groups.
        project.viewer_group, _ = Group.objects.get_or_create(name=GROUP_NAME.format(id=project.pk, role=VIEWER))
        project.editor_group, _ = Group.objects.get_or_create(name=GROUP_NAME.format(id=project.pk, role=EDITOR))
        project.save(update_fields=["viewer_group", "editor_group"])

        if project.project_leader_id is None:
            continue

        # Leader becomes an editor, in the editor group only.
        ProjectMembership.objects.update_or_create(
            project=project,
            user_id=project.project_leader_id,
            defaults={"role": EDITOR},
        )
        UserGroup.objects.get_or_create(user_id=project.project_leader_id, group=project.editor_group)
        UserGroup.objects.filter(user_id=project.project_leader_id, group=project.viewer_group).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0008_project_membership"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
