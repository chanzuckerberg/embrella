import time

import pytest
from stores.models import Path

from tem.models import (
    AcquisitionSettings,
    ImagingWorkflow,
    MsiSession,
    SessionPlan,
    SessionPlanPathBinding,
)

# Fixtures (test_user, microscope, camera, magnification, software,
# session_plan, project, grid) live in tem/tests/conftest.py.


def _today():
    """The yymmmdd part of a suggested name, built the way suggest_name builds it."""
    return time.strftime("%y%b%d").lower()


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

    def test_plan_option_carries_its_tiers(self, client, test_user, session_plan):
        client.force_login(test_user)
        plan = client.get("/tem/v1/sessions/form-options/").json()["session_plans"][0]
        assert plan["workflow"] == str(session_plan.imaging_workflow)
        assert plan["scope"] == session_plan.scope.name
        assert plan["software"] == str(session_plan.software)
        assert plan["camera"] == session_plan.camera.name

    def test_plan_option_carries_acquisition_defaults(self, client, test_user, session_plan):
        session_plan.acquisition_defaults = AcquisitionSettings.objects.create(label="k2", super_resolution=True)
        session_plan.save()
        client.force_login(test_user)

        plan = client.get("/tem/v1/sessions/form-options/").json()["session_plans"][0]

        assert plan["acquisition_defaults"] == {"super_resolution": True}

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
        assert response.status_code == 401


@pytest.mark.django_db
class TestListSessions:
    def test_newest_first_with_prefixed_names(self, client, test_user, session_plan):
        client.force_login(test_user)
        for name in ["25dec31b", "26sep01a", "s26sep02a"]:
            MsiSession.objects.create(name=name, session_plan=session_plan)

        data = client.get("/tem/v1/sessions/").json()

        assert [s["name"] for s in data["sessions"]] == ["s26sep02a", "26sep01a", "25dec31b"]

    def test_item_carries_its_plan(self, client, test_user, session_plan):
        client.force_login(test_user)
        MsiSession.objects.create(name="26sep01a", session_plan=session_plan)

        item = client.get("/tem/v1/sessions/").json()["sessions"][0]

        assert item == {
            "name": "26sep01a",
            "scope": session_plan.scope.name,
            "software": str(session_plan.software),
            "camera": session_plan.camera.name,
            "workflow": str(session_plan.imaging_workflow),
        }

    def test_requires_authentication(self, client):
        assert client.get("/tem/v1/sessions/").status_code == 401


@pytest.mark.django_db
class TestSessionDetail:
    def test_same_shape_as_created_session(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        MsiSession.objects.create(name="26sep01a", session_plan=session_plan, project=project, grid=grid)

        data = client.get("/tem/v1/sessions/26sep01a/").json()

        assert data["name"] == "26sep01a"
        assert data["project_name"] == project.name
        assert data["grid_name"] == str(grid)
        assert data["session_plan_name"] == str(session_plan)
        assert set(data) >= {"frames", "sums", "mdocs", "parents", "atlas", "legacy_url"}

    def test_tolerates_missing_project_and_grid(self, client, test_user, session_plan):
        client.force_login(test_user)
        MsiSession.objects.create(name="26sep01a", session_plan=session_plan)

        data = client.get("/tem/v1/sessions/26sep01a/").json()

        assert data["project_name"] is None
        assert data["grid_name"] is None

    def test_unknown_session_404(self, client, test_user):
        client.force_login(test_user)

        assert client.get("/tem/v1/sessions/nope/").status_code == 404

    def test_literal_routes_still_win(self, client, test_user, session_plan, project):
        """form-options/ and suggest-name/ must not be swallowed by the <name>/ route."""
        client.force_login(test_user)

        assert "session_plans" in client.get("/tem/v1/sessions/form-options/").json()
        assert "suggested_name" in client.get("/tem/v1/sessions/suggest-name/").json()


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

    def test_applies_plan_prefix(self, client, test_user, session_plan):
        client.force_login(test_user)
        session_plan.name_prefix = "s"
        session_plan.save()
        response = client.get(f"/tem/v1/sessions/suggest-name/?session_plan_id={session_plan.id}")
        assert response.json()["suggested_name"] == f"s{_today()}a"

    def test_prefixed_and_plain_names_increment_independently(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)
        session_plan.name_prefix = "s"
        session_plan.save()
        for name in (f"s{_today()}a", f"{_today()}a", f"{_today()}b"):
            MsiSession.objects.create(name=name, session_plan=session_plan, project=project, grid=grid)

        prefixed = client.get(f"/tem/v1/sessions/suggest-name/?session_plan_id={session_plan.id}")
        plain = client.get("/tem/v1/sessions/suggest-name/")
        assert prefixed.json()["suggested_name"] == f"s{_today()}b"
        assert plain.json()["suggested_name"] == f"{_today()}c"

    @pytest.mark.parametrize("query", ["", "?session_plan_id=99999", "?session_plan_id=abc"])
    def test_falls_back_to_no_prefix(self, client, test_user, query):
        client.force_login(test_user)
        response = client.get(f"/tem/v1/sessions/suggest-name/{query}")
        assert response.status_code == 200
        assert response.json()["suggested_name"] == f"{_today()}a"

    def test_requires_authentication(self, client):
        response = client.get("/tem/v1/sessions/suggest-name/")
        assert response.status_code == 401


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
        assert response.status_code == 401


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

    def _create(self, client, session_plan, project, grid, **extra):
        return client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06f",
                "session_plan_id": session_plan.id,
                "project_id": project.id,
                "grid_id": grid.id,
                **extra,
            },
            content_type="application/json",
        )

    def test_posted_acquisition_wins_over_the_plan_profile(self, client, test_user, session_plan, project, grid):
        session_plan.acquisition_defaults = AcquisitionSettings.objects.create(label="k2", super_resolution=True)
        session_plan.save()
        client.force_login(test_user)

        response = self._create(client, session_plan, project, grid, super_resolution=False)

        assert response.status_code == 201
        assert response.json()["acquisition"] == {"super_resolution": False}
        session = MsiSession.objects.get(name="26mar06f")
        assert session.super_resolution is False
        assert session.acquisition.pk != session_plan.acquisition_defaults.pk

    def test_omitted_acquisition_copies_the_plan_profile(self, client, test_user, session_plan, project, grid):
        session_plan.acquisition_defaults = AcquisitionSettings.objects.create(label="k2", super_resolution=True)
        session_plan.save()
        client.force_login(test_user)

        response = self._create(client, session_plan, project, grid)

        assert response.status_code == 201
        assert MsiSession.objects.get(name="26mar06f").super_resolution is True

    def test_plan_without_profile_still_gets_a_row(self, client, test_user, session_plan, project, grid):
        client.force_login(test_user)

        response = self._create(client, session_plan, project, grid)

        assert response.status_code == 201
        assert response.json()["acquisition"] == {"super_resolution": False}
        assert str(MsiSession.objects.get(name="26mar06f").acquisition) == "snapshot 26mar06f"

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
        assert response.status_code == 401


@pytest.mark.django_db
class TestCreatedSessionPaths:
    """The per-role halves the created-session dialog renders.

    Since the split, a directory alone says less than the old combined template did, so the
    response carries the file pattern beside it. SessionCreatedDialog.tsx shows both.
    """

    @pytest.fixture
    def created(self, client, test_user, plan_with_frames, project, grid):
        client.force_login(test_user)
        response = client.post(
            "/tem/v1/sessions/",
            data={
                "name": "26mar06f",
                "session_plan_id": plan_with_frames.id,
                "project_id": project.id,
                "grid_id": grid.id,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        return response.json()

    def test_reports_the_directory_and_the_filenames_expected_in_it(self, created):
        assert created["frames"] == {
            "directory": "/hpc/instruments/czii.TestScope/OffloadData/26mar06f/",
            "pattern": "*.eer",
        }

    def test_a_role_the_software_does_not_emit_is_null_on_both_halves(self, created):
        assert created["sums"] == {"directory": None, "pattern": None}

    def test_creates_one_path_row_and_no_bindings(self, created):
        """Path rows scale with sessions, bindings with plans -- creating a session writes
        zero of the latter."""
        assert Path.objects.count() == 1
        assert SessionPlanPathBinding.objects.count() == 0
