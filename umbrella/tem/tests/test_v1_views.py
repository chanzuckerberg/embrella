import pytest

from tem.models import (
    ImagingWorkflow,
    MsiSession,
    SessionPlan,
)

# Fixtures (test_user, microscope, camera, magnification, software,
# session_plan, project, grid) live in tem/tests/conftest.py.


@pytest.mark.django_db
class TestFormOptions:
    def test_returns_session_plans_and_projects(self, client, test_user, session_plan, project):
        client.force_login(test_user)
        response = client.get("/tem/v1/sessions/form-options/")
        assert response.status_code == 200
        data = response.json()
        assert "session_plans" in data
        assert "projects" in data
        assert len(data["session_plans"]) == 1
        assert data["session_plans"][0]["id"] == session_plan.id
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "TestProject"

    def test_filters_to_tomo_and_sngl_workflows(self, client, test_user, microscope, camera, software):
        client.force_login(test_user)
        tomo_wf = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
        scrn_wf = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="scrn")
        SessionPlan.objects.create(scope=microscope, camera=camera, imaging_workflow=tomo_wf, software=software)
        SessionPlan.objects.create(scope=microscope, camera=camera, imaging_workflow=scrn_wf, software=software)

        response = client.get("/tem/v1/sessions/form-options/")
        data = response.json()
        assert len(data["session_plans"]) == 1

    def test_requires_authentication(self, client):
        response = client.get("/tem/v1/sessions/form-options/")
        assert response.status_code == 302
        assert "login" in response.url


@pytest.mark.django_db
class TestSuggestName:
    def test_returns_suggested_name(self, client, test_user):
        client.force_login(test_user)
        response = client.get("/tem/v1/sessions/suggest-name/")
        assert response.status_code == 200
        data = response.json()
        assert "suggested_name" in data
        assert len(data["suggested_name"]) > 0
        assert data["suggested_name"].endswith("a")

    def test_requires_authentication(self, client):
        response = client.get("/tem/v1/sessions/suggest-name/")
        assert response.status_code == 302
        assert "login" in response.url


@pytest.mark.django_db
class TestGetMagnifications:
    def test_returns_magnifications_for_plan(self, client, test_user, session_plan, magnification):
        client.force_login(test_user)
        response = client.get(f"/tem/v1/magnifications/?session_plan_id={session_plan.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == magnification.id
        assert data[0]["nominal_mag"] == 50000

    def test_returns_empty_for_missing_plan(self, client, test_user):
        client.force_login(test_user)
        response = client.get("/tem/v1/magnifications/")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_empty_for_nonexistent_plan(self, client, test_user):
        client.force_login(test_user)
        response = client.get("/tem/v1/magnifications/?session_plan_id=99999")
        assert response.status_code == 200
        assert response.json() == []

    def test_requires_authentication(self, client):
        response = client.get("/tem/v1/magnifications/?session_plan_id=1")
        assert response.status_code == 302
        assert "login" in response.url


@pytest.mark.django_db
class TestCreateSession:
    def test_creates_session_successfully(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06a",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "26mar06a"
        assert "id" in data

        session = MsiSession.objects.get(name="26mar06a")
        assert session.project == project
        assert session.grid == grid
        assert session.session_plan == session_plan
        assert session.user == test_user

    def test_creates_session_with_magnification(self, client, test_user, session_plan, project, grid, magnification):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06b",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
                "magnification_id": magnification.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        session = MsiSession.objects.get(name="26mar06b")
        assert session.magnification == magnification

    def test_creates_session_without_magnification(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06c",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
                "magnification_id": None,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        session = MsiSession.objects.get(name="26mar06c")
        assert session.magnification is None

    def test_rejects_duplicate_name(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        MsiSession.objects.create(
            name="existing",
            session_plan=session_plan,
            project=project,
            grid=grid,
            user=test_user,
        )
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "existing",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "name" in response.json()

    def test_rejects_special_characters_in_name(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "bad@name",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "name" in response.json()

    def test_rejects_spaces_in_name(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "bad name",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_rejects_missing_required_fields(self, client, test_user):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={"name": "26mar06d"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_requires_authentication(self, client, session_plan, project, grid):
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06e",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 302
        assert "login" in response.url
