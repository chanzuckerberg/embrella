"""API tests for /projects/v1/projects/ and its members action."""

import pytest
from django.contrib.auth.models import User
from people.models import Institution, Person
from rest_framework.test import APIClient

from projects import services
from projects.models import Project, ProjectMembership, ProjectRole

PROJECTS_URL = "/projects/v1/projects/"


def _detail_url(project):
    return f"{PROJECTS_URL}{project.pk}/"


def _members_url(project):
    return f"{PROJECTS_URL}{project.pk}/members/"


def _client(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def leader(db):
    return User.objects.create_user(username="leader", password="pw")


@pytest.fixture
def viewer(db):
    return User.objects.create_user(username="viewer", password="pw")


@pytest.fixture
def editor(db):
    return User.objects.create_user(username="editor", password="pw")


@pytest.fixture
def staff(db):
    return User.objects.create_user(username="staff", password="pw", is_staff=True)


@pytest.fixture
def project(leader, viewer, editor):
    project = Project.objects.create(name="TRD99", project_leader=leader)
    services.add_member(project, viewer, ProjectRole.VIEWER)
    services.add_member(project, editor, ProjectRole.EDITOR)
    return project


@pytest.mark.django_db
class TestAuth:
    def test_requires_login(self):
        response = APIClient().get(PROJECTS_URL, HTTP_ACCEPT="application/json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestProjectCrud:
    def test_list_includes_members(self, project, viewer):
        response = _client(viewer).get(PROJECTS_URL)

        assert response.status_code == 200
        members = {m["username"]: m["role"] for m in response.json()[0]["members"]}
        assert members == {"leader": "editor", "viewer": "viewer", "editor": "editor"}

    def test_create_makes_creator_editor(self, viewer):
        response = _client(viewer).post(PROJECTS_URL, {"name": "NEW01"}, format="json")

        assert response.status_code == 201, response.content
        project = Project.objects.get(name="NEW01")
        assert ProjectMembership.objects.get(project=project, user=viewer).role == ProjectRole.EDITOR

    def test_viewer_cannot_update(self, project, viewer):
        response = _client(viewer).patch(_detail_url(project), {"description": "x"}, format="json")
        assert response.status_code == 403

    def test_editor_can_update(self, project, editor):
        response = _client(editor).patch(_detail_url(project), {"description": "x"}, format="json")
        assert response.status_code == 200

    def test_institutions_and_contributors_round_trip(self, project, editor):
        institution = Institution.objects.create(name="CZ Imaging Institute")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace", institution=institution)

        response = _client(editor).patch(
            _detail_url(project),
            {"institution_ids": [institution.pk], "contributor_ids": [person.pk]},
            format="json",
        )

        assert response.status_code == 200, response.content
        body = response.json()
        assert [i["name"] for i in body["institutions"]] == ["CZ Imaging Institute"]
        assert [c["family_name"] for c in body["contributors"]] == ["Lovelace"]


@pytest.mark.django_db
class TestMembersAction:
    def test_list_shape(self, project, viewer):
        response = _client(viewer).get(_members_url(project))

        assert response.status_code == 200
        assert response.json()[0].keys() == {"user_id", "username", "role"}

    def test_viewer_cannot_add(self, project, viewer, staff):
        response = _client(viewer).post(_members_url(project), {"user": staff.pk}, format="json")
        assert response.status_code == 403

    def test_editor_adds_member(self, project, editor):
        newcomer = User.objects.create_user(username="newcomer", password="pw")

        response = _client(editor).post(_members_url(project), {"user": newcomer.pk, "role": "viewer"}, format="json")

        assert response.status_code == 201, response.content
        assert newcomer.groups.filter(pk=project.viewer_group_id).exists()

    def test_staff_changes_role(self, project, staff, viewer):
        response = _client(staff).patch(_members_url(project), {"user": viewer.pk, "role": "editor"}, format="json")

        assert response.status_code == 200, response.content
        assert ProjectMembership.objects.get(project=project, user=viewer).role == ProjectRole.EDITOR

    def test_patch_non_member_404(self, project, staff):
        response = _client(staff).patch(_members_url(project), {"user": staff.pk, "role": "editor"}, format="json")
        assert response.status_code == 404

    def test_editor_removes_member(self, project, editor, viewer):
        response = _client(editor).delete(_members_url(project), {"user": viewer.pk}, format="json")

        assert response.status_code == 204
        assert not viewer.groups.exists()

    def test_leader_cannot_be_removed(self, project, staff, leader):
        response = _client(staff).delete(_members_url(project), {"user": leader.pk}, format="json")
        assert response.status_code == 400

    def test_leader_cannot_be_demoted(self, project, staff, leader):
        response = _client(staff).patch(_members_url(project), {"user": leader.pk, "role": "viewer"}, format="json")
        assert response.status_code == 400
