"""History capture: every grid / storage action writes a simple-history row stamped with the acting user."""

import pytest

from cryo_grids.history import ChangeReason, edit_reason
from cryo_grids.models import (
    Cane,
    Dewar,
    GridLabel,
    Label,
    Puck,
)

CREATED = "+"
CHANGED = "~"
DELETED = "-"


def latest(obj):
    return obj.history.order_by("-history_id").first()


@pytest.mark.django_db
class TestGridHistory:
    def test_create_writes_created_row(self, test_grid):
        assert test_grid.history.count() == 1
        assert latest(test_grid).history_type == CREATED

    def test_updated_on_not_tracked(self, test_grid):
        assert not hasattr(latest(test_grid), "updated_on")

    def test_move_grid(self, logged_in_client, test_user, test_grid, test_box_b):
        response = logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/move/",
            data={"destination_grid_box_id": test_box_b.id, "destination_position": 2},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(test_grid)
        assert row.history_type == CHANGED
        assert row.grid_box_id == test_box_b.id
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.MOVED

    def test_trash_grid(self, logged_in_client, test_user, test_grid):
        response = logged_in_client.post(
            f"/cryo_grids/update-grid-trashed/{test_grid.id}/",
            data={"trashed": True},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(test_grid)
        assert row.trashed is True
        assert row.grid_box_id is None
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.TRASHED

    def test_restore_grid(self, logged_in_client, test_grid):
        url = f"/cryo_grids/update-grid-trashed/{test_grid.id}/"
        logged_in_client.post(url, data={"trashed": True}, content_type="application/json")
        logged_in_client.post(url, data={"trashed": False}, content_type="application/json")

        assert latest(test_grid).history_change_reason == ChangeReason.RESTORED

    @pytest.mark.parametrize(("clipped", "reason"), [(True, ChangeReason.CLIPPED), (False, ChangeReason.UNCLIPPED)])
    def test_clip_toggle(self, logged_in_client, test_grid, clipped, reason):
        logged_in_client.post(
            f"/cryo_grids/update-grid-clipped/{test_grid.id}/",
            data={"clipped": clipped},
            content_type="application/json",
        )

        assert latest(test_grid).history_change_reason == reason

    def test_edit_grid(self, logged_in_client, test_grid):
        response = logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/update/",
            data={"blot_time": 4.5},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(test_grid)
        assert row.blot_time == 4.5
        assert row.history_change_reason == ChangeReason.EDITED


@pytest.mark.django_db
class TestBulkWritesRecordHistory:
    """These paths used queryset.update(), which bypasses simple-history."""

    def test_clip_all_in_box(self, logged_in_client, test_user, test_grid, test_box_a):
        response = logged_in_client.post(f"/cryo_grids/v1/grids/clip-all-in-box/{test_box_a.id}/")
        assert response.status_code == 200

        test_grid.refresh_from_db()
        assert test_grid.clipped is True

        row = latest(test_grid)
        assert row.clipped is True
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.CLIPPED

    def test_delete_grid_box_trashes_with_history(self, logged_in_client, test_user, test_grid, test_box_a):
        response = logged_in_client.delete(f"/api/list/pucks/grid-box/{test_box_a.id}/")
        assert response.status_code == 200

        row = latest(test_grid)
        assert row.trashed is True
        assert row.grid_box_id is None
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.BOX_DELETED

    def test_delete_puck_trashes_with_history(self, logged_in_client, test_user, test_grid, test_puck):
        response = logged_in_client.delete(f"/api/list/pucks/{test_puck.id}/")
        assert response.status_code == 200

        row = latest(test_grid)
        assert row.trashed is True
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.PUCK_DELETED


@pytest.mark.django_db
class TestLabelHistory:
    def test_add_and_remove_label(self, logged_in_client, test_user, test_grid):
        label = Label.objects.create(name="history-test", color="#43a047")
        url = f"/cryo_grids/v1/grids/{test_grid.id}/update-labels/"

        logged_in_client.patch(url, data={"label_ids": [label.id]}, content_type="application/json")
        logged_in_client.patch(url, data={"label_ids": []}, content_type="application/json")

        rows = GridLabel.history.filter(grid_id=test_grid.id).order_by("history_id")
        assert [r.history_type for r in rows] == [CREATED, DELETED]
        assert all(r.label_id == label.id for r in rows)
        assert all(r.history_user == test_user for r in rows)

        # updated_on bump must not add empty grid rows
        assert test_grid.history.count() == 1


@pytest.mark.django_db
class TestContainerHistory:
    def test_move_grid_box(self, logged_in_client, test_user, test_box_a, test_puck):
        other_puck = Puck.objects.create(name="OtherPuck", cane=test_puck.cane, position_in_cane=2)

        response = logged_in_client.patch(
            f"/api/list/pucks/grid-box/{test_box_a.id}/move/",
            data={"puck_id": other_puck.id, "position_in_puck": 3},
            content_type="application/json",
        )
        assert response.status_code == 200

        row = latest(test_box_a)
        assert row.history_type == CHANGED
        assert (row.puck_id, row.position_in_puck) == (other_puck.id, 3)
        assert row.history_user == test_user
        assert row.history_change_reason == ChangeReason.MOVED

    @pytest.mark.parametrize(
        ("changes", "reason"),
        [({"position_in_cane": 5}, ChangeReason.MOVED), ({"name": "Renamed"}, ChangeReason.EDITED)],
    )
    def test_update_puck(self, logged_in_client, test_user, test_puck, changes, reason):
        response = logged_in_client.patch(
            f"/api/list/pucks/{test_puck.id}/", data=changes, content_type="application/json"
        )
        assert response.status_code == 200

        row = latest(test_puck)
        assert row.history_user == test_user
        assert row.history_change_reason == reason

    @pytest.mark.parametrize("model", [Puck, Cane, Dewar])
    def test_containers_tracked(self, test_puck, model):
        assert model.history.count() >= 1


class TestEditReason:
    def test_location_change_is_move(self, test_puck):
        assert edit_reason(test_puck, {"position_in_cane": 9}) == ChangeReason.MOVED

    def test_same_location_is_edit(self, test_puck):
        assert edit_reason(test_puck, {"cane": test_puck.cane, "name": "x"}) == ChangeReason.EDITED
