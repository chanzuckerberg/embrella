import json

import pytest

from cryo_grids.models import Puck

pytestmark = pytest.mark.django_db

PUCKS_URL = "/api/list/pucks/"
CANES_URL = "/api/list/canes/"
GRID_BOXES_URL = "/cryo_grids/v1/grid-boxes/"


def _row(response, puck_id):
    return next(p for p in response.json()["pucks"] if p["id"] == puck_id)


def test_list_counts_grid_boxes(logged_in_client, test_puck, test_box_a, test_box_b):
    response = logged_in_client.get(PUCKS_URL)

    assert _row(response, test_puck.pk)["grid_box_count"] == 2


def test_list_counts_empty_puck(logged_in_client, test_puck):
    response = logged_in_client.get(PUCKS_URL)

    assert _row(response, test_puck.pk)["grid_box_count"] == 0


def test_create_returns_zero_count(logged_in_client, test_user):
    # A created instance skips the queryset annotation; the field falls back to its default.
    data = {"name": "NewPuck", "color": Puck._meta.get_field("color").default, "user": test_user.pk}
    response = logged_in_client.post(PUCKS_URL, data=data, content_type="application/json")

    assert response.json()["puck"]["grid_box_count"] == 0


def test_grid_owner_filter_finds_pucks_holding_their_grids(logged_in_client, test_puck, test_grid):
    # test_grid sits in test_puck, which has no owner; the filter goes by grid owner.
    other = Puck.objects.create(name="Other", position_in_cane=2)

    response = logged_in_client.get(PUCKS_URL, {"grid_owner_id": test_grid.user_id})
    ids = {p["id"] for p in response.json()["pucks"]}

    assert test_puck.pk in ids
    assert other.pk not in ids


def test_grid_owner_filter_skips_trashed_grids(logged_in_client, test_puck, test_grid):
    test_grid.trashed = True
    test_grid.save()

    response = logged_in_client.get(PUCKS_URL, {"grid_owner_id": test_grid.user_id})

    assert response.json()["pucks"] == []


def test_grid_owner_filter_keeps_box_count(logged_in_client, test_puck, test_grid, test_box_b):
    # Two boxes, one holding the grid: the filter's join must not change the count.
    response = logged_in_client.get(PUCKS_URL, {"grid_owner_id": test_grid.user_id})

    assert _row(response, test_puck.pk)["grid_box_count"] == 2


def test_cane_list_includes_dewar_name(logged_in_client, test_puck):
    response = logged_in_client.get(CANES_URL)
    cane = next(c for c in response.json()["canes"] if c["id"] == test_puck.cane_id)

    assert cane["dewar_name"] == "DewarA"


def test_grid_box_search_includes_puck_id(logged_in_client, test_puck, test_box_a):
    q = json.dumps([{"category": "search", "value": [test_box_a.name]}])
    response = logged_in_client.get(GRID_BOXES_URL, {"q": q})
    row = next(r for r in response.json()["result"] if r["gridBox"]["id"] == test_box_a.pk)

    assert row["puckId"] == test_puck.pk


def test_grid_box_positions_report_numeric_grid_id(logged_in_client, test_puck, test_grid):
    # The picker matches position grid ids against numeric ids from other endpoints.
    response = logged_in_client.get(f"{PUCKS_URL}{test_puck.pk}/grid-box/{test_grid.grid_box.position_in_puck}/")
    position = next(p for p in response.json()["grid_box"]["positions"] if p["occupied"])

    assert position["grid_id"] == test_grid.pk
