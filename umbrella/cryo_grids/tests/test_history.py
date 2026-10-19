"""History capture: every grid / storage action writes a simple-history row stamped with the acting user."""

import pytest
from django.contrib.auth.models import User

from cryo_grids.history import ChangeReason, edit_reason
from cryo_grids.models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    Dewar,
    GridLabel,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Site,
)

CREATED = "+"
CHANGED = "~"
DELETED = "-"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="historian", password="testpass")


@pytest.fixture
def site(db):
    return Site.objects.create(name="HistorySite")


@pytest.fixture
def freezing_session(db, user, site):
    device = PlungeFreezingDevice.objects.create(name="HistoryDevice", site=site)
    return PlungeFreezingSession.objects.create(user=user, device=device)


@pytest.fixture
def puck(db, site):
    dewar = Dewar.objects.create(name="HistoryDewar", site=site)
    cane = Cane.objects.create(name="HistoryCane", dewar=dewar)
    return Puck.objects.create(name="HistoryPuck", cane=cane, position_in_cane=1)


@pytest.fixture
def box_a(db, puck):
    return CryoGridBox.objects.create(name="BoxA", puck=puck, position_in_puck=1)


@pytest.fixture
def box_b(db, puck):
    return CryoGridBox.objects.create(name="BoxB", puck=puck, position_in_puck=2)


@pytest.fixture
def grid(db, user, freezing_session, box_a):
    return CryoGrid.objects.create(
        name="grid1", user=user, freezing_session=freezing_session, grid_box=box_a, position_in_box=1
    )


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def latest(obj):
    return obj.history.order_by("-history_id").first()


@pytest.mark.django_db
class TestGridHistory:
    def test_create_writes_created_row(self, grid):
        assert grid.history.count() == 1
        assert latest(grid).history_type == CREATED

    def test_updated_on_not_tracked(self, grid):
        assert not hasattr(latest(grid), "updated_on")

    def test_move_grid(self, logged_in, user, grid, box_b):
        response = logged_in.patch(
            f"/cryo_grids/v1/grids/{grid.id}/move/",
            data={"destination_grid_box_id": box_b.id, "destination_position": 2},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(grid)
        assert row.history_type == CHANGED
        assert row.grid_box_id == box_b.id
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.MOVED

    def test_trash_grid(self, logged_in, user, grid):
        response = logged_in.post(
            f"/cryo_grids/update-grid-trashed/{grid.id}/",
            data={"trashed": True},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(grid)
        assert row.trashed is True
        assert row.grid_box_id is None
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.TRASHED

    def test_restore_grid(self, logged_in, grid):
        url = f"/cryo_grids/update-grid-trashed/{grid.id}/"
        logged_in.post(url, data={"trashed": True}, content_type="application/json")
        logged_in.post(url, data={"trashed": False}, content_type="application/json")

        assert latest(grid).history_change_reason == ChangeReason.RESTORED

    @pytest.mark.parametrize(("clipped", "reason"), [(True, ChangeReason.CLIPPED), (False, ChangeReason.UNCLIPPED)])
    def test_clip_toggle(self, logged_in, grid, clipped, reason):
        logged_in.post(
            f"/cryo_grids/update-grid-clipped/{grid.id}/",
            data={"clipped": clipped},
            content_type="application/json",
        )

        assert latest(grid).history_change_reason == reason

    def test_edit_grid(self, logged_in, grid):
        response = logged_in.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update/",
            data={"blot_time": 4.5},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(grid)
        assert row.blot_time == 4.5
        assert row.history_change_reason == ChangeReason.EDITED


@pytest.mark.django_db
class TestBulkWritesRecordHistory:
    """These paths used queryset.update(), which bypasses simple-history."""

    def test_clip_all_in_box(self, logged_in, user, grid, box_a):
        response = logged_in.post(f"/cryo_grids/v1/grids/clip-all-in-box/{box_a.id}/")
        assert response.status_code == 200

        grid.refresh_from_db()
        assert grid.clipped is True

        row = latest(grid)
        assert row.clipped is True
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.CLIPPED

    def test_delete_grid_box_trashes_with_history(self, logged_in, user, grid, box_a):
        response = logged_in.delete(f"/api/list/pucks/grid-box/{box_a.id}/")
        assert response.status_code == 200

        row = latest(grid)
        assert row.trashed is True
        assert row.grid_box_id is None
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.BOX_DELETED

    def test_delete_puck_trashes_with_history(self, logged_in, user, grid, puck):
        response = logged_in.delete(f"/api/list/pucks/{puck.id}/")
        assert response.status_code == 200

        row = latest(grid)
        assert row.trashed is True
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.PUCK_DELETED


@pytest.mark.django_db
class TestLabelHistory:
    def test_add_and_remove_label(self, logged_in, user, grid):
        label = Label.objects.create(name="history-test", color="#43a047")
        url = f"/cryo_grids/v1/grids/{grid.id}/update-labels/"

        logged_in.patch(url, data={"label_ids": [label.id]}, content_type="application/json")
        logged_in.patch(url, data={"label_ids": []}, content_type="application/json")

        rows = GridLabel.history.filter(grid_id=grid.id).order_by("history_id")
        assert [r.history_type for r in rows] == [CREATED, DELETED]
        assert all(r.label_id == label.id for r in rows)
        assert all(r.history_user == user for r in rows)

        # updated_on bump must not add empty grid rows
        assert grid.history.count() == 1


@pytest.mark.django_db
class TestContainerHistory:
    def test_move_grid_box(self, logged_in, user, box_a, puck):
        other_puck = Puck.objects.create(name="OtherPuck", cane=puck.cane, position_in_cane=2)

        response = logged_in.patch(
            f"/api/list/pucks/grid-box/{box_a.id}/move/",
            data={"puck_id": other_puck.id, "position_in_puck": 3},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(box_a)
        assert row.history_type == CHANGED
        assert (row.puck_id, row.position_in_puck) == (other_puck.id, 3)
        assert row.history_user == user
        assert row.history_change_reason == ChangeReason.MOVED

    @pytest.mark.parametrize(
        ("changes", "reason"),
        [({"position_in_cane": 5}, ChangeReason.MOVED), ({"name": "Renamed"}, ChangeReason.EDITED)],
    )
    def test_update_puck(self, logged_in, user, puck, changes, reason):
        response = logged_in.patch(f"/api/list/pucks/{puck.id}/", data=changes, content_type="application/json")
        assert response.status_code == 200

        row = latest(puck)
        assert row.history_user == user
        assert row.history_change_reason == reason

    @pytest.mark.parametrize("model", [Puck, Cane, Dewar])
    def test_containers_tracked(self, puck, model):
        assert model.history.count() >= 1


class TestEditReason:
    def test_location_change_is_move(self, puck):
        assert edit_reason(puck, {"position_in_cane": 9}) == ChangeReason.MOVED

    def test_same_location_is_edit(self, puck):
        assert edit_reason(puck, {"cane": puck.cane, "name": "x"}) == ChangeReason.EDITED
