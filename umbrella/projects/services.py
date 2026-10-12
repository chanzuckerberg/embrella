"""Project membership and role groups.

Each project owns two auth Groups, the grantees for object permissions:

    project:<id>:viewer   ← members with role VIEWER
    project:<id>:editor   ← members with role EDITOR

A member sits in exactly one of them. Callers change membership through
these functions; nothing else should touch the groups directly.
"""

from django.contrib.auth.models import Group

from projects.models import Project, ProjectMembership, ProjectRole

GROUP_NAME = "project:{id}:{role}"


def ensure_groups(project: Project) -> None:
    """Create the project's role groups if missing."""
    changed = []

    if project.viewer_group_id is None:
        project.viewer_group, _ = Group.objects.get_or_create(name=_group_name(project, ProjectRole.VIEWER))
        changed.append("viewer_group")

    if project.editor_group_id is None:
        project.editor_group, _ = Group.objects.get_or_create(name=_group_name(project, ProjectRole.EDITOR))
        changed.append("editor_group")

    if changed:
        project.save(update_fields=changed)


def ensure_leader(project: Project) -> None:
    """Give the project leader an EDITOR membership."""
    if project.project_leader_id is None:
        return

    membership, created = ProjectMembership.objects.get_or_create(
        project=project,
        user_id=project.project_leader_id,
        defaults={"role": ProjectRole.EDITOR},
    )
    if not created and membership.role != ProjectRole.EDITOR:
        set_role(membership, ProjectRole.EDITOR)


def add_member(project: Project, user, role: ProjectRole) -> ProjectMembership:
    """Add ``user`` to ``project``, or update their role if already a member."""
    membership, _ = ProjectMembership.objects.update_or_create(
        project=project,
        user=user,
        defaults={"role": role},
    )
    return membership


def set_role(membership: ProjectMembership, role: ProjectRole) -> None:
    membership.role = role
    membership.save(update_fields=["role"])


def remove_member(project: Project, user) -> None:
    # Queryset delete still fires post_delete, which clears the groups.
    ProjectMembership.objects.filter(project=project, user=user).delete()


def sync_groups(membership: ProjectMembership) -> None:
    """Put the member in their role's group and out of the other."""
    project = membership.project
    ensure_groups(project)

    keep = _role_group(project, membership.role)
    drop = _role_group(project, _other_role(membership.role))

    membership.user.groups.add(keep)
    membership.user.groups.remove(drop)


def clear_groups(project: Project, user_id: int) -> None:
    """Remove a user from both of the project's groups."""
    group_ids = [gid for gid in (project.viewer_group_id, project.editor_group_id) if gid]
    Group.user_set.through.objects.filter(user_id=user_id, group_id__in=group_ids).delete()


def can_manage(user, project: Project) -> bool:
    """Staff, the project leader, and editors may edit a project and its members."""
    if user.is_staff or project.project_leader_id == user.id:
        return True

    return project.memberships.filter(user=user, role=ProjectRole.EDITOR).exists()


def _group_name(project: Project, role: ProjectRole) -> str:
    return GROUP_NAME.format(id=project.pk, role=role.value)


def _role_group(project: Project, role: ProjectRole) -> Group:
    return project.editor_group if role == ProjectRole.EDITOR else project.viewer_group


def _other_role(role: ProjectRole) -> ProjectRole:
    return ProjectRole.VIEWER if role == ProjectRole.EDITOR else ProjectRole.EDITOR
