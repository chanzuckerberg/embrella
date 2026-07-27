import datetime

import pytest
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.utils import timezone

from cryo_grids.models import CryoGrid, GridLabel, Label, PlungeFreezingDevice, PlungeFreezingSession, Site


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="testpass")


@pytest.fixture
def site(db):
    return Site.objects.create(name="TestSite")


@pytest.fixture
def freezing_device(db, site):
    return PlungeFreezingDevice.objects.create(name="TestDevice", site=site)


@pytest.fixture
def freezing_session(db, test_user, freezing_device):
    return PlungeFreezingSession.objects.create(user=test_user, device=freezing_device)


@pytest.fixture
def grid(db, test_user, freezing_session):
    return CryoGrid.objects.create(name="grid1", user=test_user, freezing_session=freezing_session)


@pytest.fixture
def label_a(db):
    return Label.objects.create(name="good", color="#43a047")


@pytest.fixture
def label_b(db):
    return Label.objects.create(name="bad", color="#e53935")


@pytest.fixture
def label_c(db):
    return Label.objects.create(name="ok", color="#fb8c00")


# ── Label Model Tests ──


@pytest.mark.django_db
class TestLabelModel:
    def test_create_label(self, label_a):
        assert label_a.name == "good"
        assert label_a.color == "#43a047"

    def test_label_unique_name(self, label_a):
        with pytest.raises(IntegrityError):
            Label.objects.create(name="good", color="#000000")

    def test_random_color_default(self, db):
        label = Label.objects.create(name="random_color_test")
        assert label.color.startswith("#")
        assert len(label.color) == 7

    def test_str(self, label_a):
        assert str(label_a) == "good"


# ── GridLabel Through Model Tests ──


@pytest.mark.django_db
class TestGridLabelModel:
    def test_add_label_to_grid(self, grid, label_a, test_user):
        gl = GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)
        assert gl.grid == grid
        assert gl.label == label_a
        assert gl.added_by == test_user
        assert grid.labels.count() == 1

    def test_unique_together(self, grid, label_a, test_user):
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)
        with pytest.raises(IntegrityError):
            GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)

    def test_multiple_labels_on_grid(self, grid, label_a, label_b, test_user):
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)
        GridLabel.objects.create(grid=grid, label=label_b, added_by=test_user)
        assert grid.labels.count() == 2


# ── LabelViewSet API Tests ──


@pytest.mark.django_db
class TestLabelViewSet:
    def test_list_labels(self, client, test_user, label_a, label_b):
        client.force_login(test_user)
        response = client.get("/api/list/labels/")
        assert response.status_code == 200
        data = response.json()
        names = [label["name"] for label in data]
        assert "good" in names
        assert "bad" in names

    def test_create_label(self, client, test_user):
        client.force_login(test_user)
        response = client.post(
            "/api/list/labels/",
            data={"name": "new_label"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_label"
        assert data["color"].startswith("#")
        label = Label.objects.get(name="new_label")
        assert label.created_by == test_user

    def test_create_label_unauthenticated(self, client):
        response = client.post(
            "/api/list/labels/",
            data={"name": "unauth_label"},
            content_type="application/json",
        )
        # Django middleware redirects to login (302) or DRF returns 403
        assert response.status_code in (302, 403)

    def test_list_ordered_by_usage(self, client, test_user, grid, label_a, label_b, label_c):
        """Labels with more grids should appear first."""
        client.force_login(test_user)
        # label_a used on 1 grid, label_b unused, label_c unused
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)

        response = client.get("/api/list/labels/")
        data = response.json()
        # label_a (1 usage) should be first
        assert data[0]["name"] == "good"


# ── Update Labels Action Tests ──


@pytest.mark.django_db
class TestUpdateLabels:
    def test_set_labels_on_grid(self, client, test_user, grid, label_a, label_b):
        client.force_login(test_user)
        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [label_a.id, label_b.id]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["labels"]) == 2
        assert grid.labels.count() == 2

    def test_remove_labels(self, client, test_user, grid, label_a, label_b):
        client.force_login(test_user)
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)
        GridLabel.objects.create(grid=grid, label=label_b, added_by=test_user)

        # Set to only label_a — label_b should be removed
        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [label_a.id]},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert grid.labels.count() == 1
        assert grid.labels.first() == label_a

    def test_clear_all_labels(self, client, test_user, grid, label_a):
        client.force_login(test_user)
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)

        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": []},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert grid.labels.count() == 0

    def test_invalid_label_ids(self, client, test_user, grid):
        client.force_login(test_user)
        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [99999]},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_invalid_label_ids_type(self, client, test_user, grid):
        client.force_login(test_user)
        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": "not_a_list"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_trashed_grid_can_still_have_labels(self, client, test_user, grid, label_a):
        client.force_login(test_user)
        grid.trashed = True
        grid.save()
        response = client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [label_a.id]},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert grid.labels.count() == 1

    def test_nonexistent_grid(self, client, test_user, label_a):
        client.force_login(test_user)
        response = client.patch(
            "/cryo_grids/v1/grids/99999/update-labels/",
            data={"label_ids": [label_a.id]},
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_added_by_tracked(self, client, test_user, grid, label_a):
        client.force_login(test_user)
        client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [label_a.id]},
            content_type="application/json",
        )
        gl = GridLabel.objects.get(grid=grid, label=label_a)
        assert gl.added_by == test_user
        assert gl.added_at is not None

    def test_idempotent(self, client, test_user, grid, label_a):
        """Setting the same labels twice shouldn't duplicate."""
        client.force_login(test_user)
        for _ in range(2):
            client.patch(
                f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
                data={"label_ids": [label_a.id]},
                content_type="application/json",
            )
        assert GridLabel.objects.filter(grid=grid).count() == 1

    def test_auto_deletes_recent_typo_label(self, client, test_user, grid):
        """A label created < 1 min ago and then removed (with 0 usage) gets auto-deleted."""
        client.force_login(test_user)
        # Create a new label via API (simulates typo)
        res = client.post(
            "/api/list/labels/",
            data={"name": "typolabel"},
            content_type="application/json",
        )
        typo_id = res.json()["id"]

        # Add it to the grid
        client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": [typo_id]},
            content_type="application/json",
        )
        assert Label.objects.filter(id=typo_id).exists()

        # Remove it immediately (within 1 min)
        client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": []},
            content_type="application/json",
        )
        # Label should be auto-deleted since it was just created and has 0 usage
        assert not Label.objects.filter(id=typo_id).exists()

    def test_preserves_old_unused_label(self, client, test_user, grid, label_a):
        """An established label removed from its last grid should NOT be auto-deleted."""
        client.force_login(test_user)
        # Backdate created_at to make it "old"
        Label.objects.filter(id=label_a.id).update(
            created_at=timezone.now() - datetime.timedelta(hours=1),
        )
        GridLabel.objects.create(grid=grid, label=label_a, added_by=test_user)

        # Remove it
        client.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update-labels/",
            data={"label_ids": []},
            content_type="application/json",
        )
        # Label should still exist — it's established, not a typo
        assert Label.objects.filter(id=label_a.id).exists()
