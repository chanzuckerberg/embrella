"""Project membership keeps the role groups in sync."""

import pytest
from django.contrib.auth.models import Group, User

from projects import services
from projects.models import Project, ProjectMembership, ProjectRole


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password="pw")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob", password="pw")


@pytest.fixture
def project(db):
    return Project.objects.create(name="TRD99")


def _group_names(user):
    return set(user.groups.values_list("name", flat=True))


@pytest.mark.django_db
class TestGroups:
    def test_project_gets_two_groups(self, project):
        assert project.viewer_group.name == f"project:{project.pk}:viewer"
        assert project.editor_group.name == f"project:{project.pk}:editor"

    def test_delete_project_drops_groups(self, project, alice):
        services.add_member(project, alice, ProjectRole.VIEWER)
        group_ids = [project.viewer_group_id, project.editor_group_id]

        project.delete()

        assert not _group_names(alice)
        assert not Group.objects.filter(id__in=group_ids).exists()


@pytest.mark.django_db
class TestMembership:
    def test_viewer_in_viewer_group_only(self, project, alice):
        services.add_member(project, alice, ProjectRole.VIEWER)

        assert _group_names(alice) == {project.viewer_group.name}

    def test_role_change_moves_group(self, project, alice):
        membership = services.add_member(project, alice, ProjectRole.VIEWER)

        services.set_role(membership, ProjectRole.EDITOR)

        assert _group_names(alice) == {project.editor_group.name}

    def test_add_existing_member_updates_role(self, project, alice):
        services.add_member(project, alice, ProjectRole.VIEWER)
        services.add_member(project, alice, ProjectRole.EDITOR)

        assert ProjectMembership.objects.get(project=project, user=alice).role == ProjectRole.EDITOR
        assert _group_names(alice) == {project.editor_group.name}

    def test_remove_member_clears_groups(self, project, alice):
        services.add_member(project, alice, ProjectRole.EDITOR)

        services.remove_member(project, alice)

        assert not _group_names(alice)
        assert list(project.members.all()) == []

    def test_reassigned_membership_clears_old_user(self, project, alice, bob):
        membership = services.add_member(project, alice, ProjectRole.VIEWER)

        membership.user = bob
        membership.save()

        assert not _group_names(alice)
        assert _group_names(bob) == {project.viewer_group.name}

    def test_other_projects_untouched(self, project, alice):
        other = Project.objects.create(name="TRD98")
        services.add_member(project, alice, ProjectRole.VIEWER)
        services.add_member(other, alice, ProjectRole.EDITOR)

        services.remove_member(project, alice)

        assert _group_names(alice) == {other.editor_group.name}


@pytest.mark.django_db
class TestLeader:
    def test_leader_becomes_editor(self, alice):
        project = Project.objects.create(name="TRD97", project_leader=alice)

        assert ProjectMembership.objects.get(project=project, user=alice).role == ProjectRole.EDITOR
        assert _group_names(alice) == {project.editor_group.name}

    def test_new_leader_promoted_from_viewer(self, project, alice):
        services.add_member(project, alice, ProjectRole.VIEWER)

        project.project_leader = alice
        project.save()

        assert ProjectMembership.objects.get(project=project, user=alice).role == ProjectRole.EDITOR


@pytest.mark.django_db
class TestCanManage:
    def test_staff(self, project, alice):
        alice.is_staff = True
        assert services.can_manage(alice, project)

    def test_leader(self, alice):
        project = Project.objects.create(name="TRD96", project_leader=alice)
        assert services.can_manage(alice, project)

    def test_editor(self, project, alice):
        services.add_member(project, alice, ProjectRole.EDITOR)
        assert services.can_manage(alice, project)

    def test_viewer(self, project, alice):
        services.add_member(project, alice, ProjectRole.VIEWER)
        assert not services.can_manage(alice, project)

    def test_outsider(self, project, alice):
        assert not services.can_manage(alice, project)
