"""
CSRF enforcement tests for cryo_grids mutating endpoints.

These lock in that session-authenticated, state-changing requests are rejected
(403) when no CSRF token is supplied, and succeed when a valid token is sent.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from cryo_grids.models import (
    CryoGrid,
    CryoGridBox,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Site,
    Specimen,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="csrf-user", password="pw")


@pytest.fixture
def puck(db, user):
    return Puck.objects.create(name="1", user=user)


@pytest.fixture
def grid(db, user):
    site = Site.objects.create(name="site")
    device = PlungeFreezingDevice.objects.create(name="dev", site=site)
    session = PlungeFreezingSession.objects.create(user=user, device=device)
    specimen = Specimen.objects.create()
    box = CryoGridBox.objects.create(
        name="b", puck=Puck.objects.create(name="2", user=user), position_in_puck=1, max_grids=4
    )
    return CryoGrid.objects.create(
        name="g",
        user=user,
        freezing_session=session,
        specimen=specimen,
        grid_box=box,
        position_in_box=1,
    )


@pytest.fixture
def label(db):
    return Label.objects.create(name="lbl", color="#fff")


def _csrf_token(client):
    """Prime the csrftoken cookie via the admin login page (renders {% csrf_token %})."""
    client.get("/admin/login/")
    return client.cookies["csrftoken"].value


@pytest.mark.django_db
class TestCsrfEnforcement:
    # --- DRF ViewSet endpoints -------------------------------------------------

    def test_puck_destroy_rejects_without_csrf(self, puck, user):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        resp = client.delete(f"/api/list/pucks/{puck.id}/")
        assert resp.status_code == 403, resp.content

    def test_puck_destroy_succeeds_with_csrf(self, puck, user):
        client = APIClient(enforce_csrf_checks=True)
        token = _csrf_token(client)
        client.force_login(user)
        resp = client.delete(f"/api/list/pucks/{puck.id}/", HTTP_X_CSRFTOKEN=token)
        assert resp.status_code != 403, resp.content

    def test_update_labels_rejects_without_csrf(self, grid, label, user):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        resp = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            {"label_ids": [label.id]},
            format="json",
        )
        assert resp.status_code == 403, resp.content

    def test_update_labels_succeeds_with_csrf(self, grid, label, user):
        client = APIClient(enforce_csrf_checks=True)
        token = _csrf_token(client)
        client.force_login(user)
        resp = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            {"label_ids": [label.id]},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert resp.status_code != 403, resp.content

    # --- Plain Django function view -------------------------------------------

    def test_trashed_status_rejects_without_csrf(self, grid, user):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        resp = client.post(
            f"/cryo_grids/update-grid-trashed/{grid.id}/",
            {"trashed": True},
            format="json",
        )
        assert resp.status_code == 403, resp.content

    def test_trashed_status_succeeds_with_csrf(self, grid, user):
        client = APIClient(enforce_csrf_checks=True)
        token = _csrf_token(client)
        client.force_login(user)
        resp = client.post(
            f"/cryo_grids/update-grid-trashed/{grid.id}/",
            {"trashed": True},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert resp.status_code != 403, resp.content
