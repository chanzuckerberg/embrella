"""Tests for ScreeningGridsViewSet filtering and the screening filterlist endpoint."""

import json

import pytest
from django.contrib.auth.models import User
from projects.models import Project

from cryo_grids.models import CryoGrid, GridLabel, Label

SCREENING_URL = "/cryo_grids/v1/screening-grids/"
FILTERLIST_URL = "/cryo_grids/v1/screening-grids/filterlist/"


def q(params):
    """Encode a list of {category, value} entries as the `q` query param."""
    return {"q": json.dumps(params)}


@pytest.fixture
def user(db):
    return User.objects.create_user(username="screener", password="pw")


@pytest.fixture
def labels(db):
    names = [
        "TBS",
        "To Be Screened",
        "To Be Collected",
        "To Be Milled",
        "Arctis",
        "Krios1",
        "P1",
        "P2",
    ]
    # These label names are seeded by migrations 0034/0035, so reuse if present.
    return {name: Label.objects.get_or_create(name=name, defaults={"color": "#1e88e5"})[0] for name in names}


@pytest.fixture
def projects(db):
    return {
        "alpha": Project.objects.create(name="Alpha"),
        "beta": Project.objects.create(name="Beta"),
    }


def make_grid(user, name, label_objs, project=None, trashed=False):
    grid = CryoGrid.objects.create(name=name, user=user, intended_project=project, trashed=trashed)
    for label in label_objs:
        GridLabel.objects.create(grid=grid, label=label, added_by=user)
    return grid


@pytest.fixture
def screening_grids(db, user, labels, projects):
    """A spread of grids exercising both status forms, microscopes, and projects."""
    return {
        # short-form status TBS + Arctis + P1 + Alpha
        "g_tbs": make_grid(user, "g_tbs", [labels["TBS"], labels["Arctis"], labels["P1"]], projects["alpha"]),
        # long-form status + Krios1 + P2 + Beta
        "g_long": make_grid(
            user, "g_long", [labels["To Be Screened"], labels["Krios1"], labels["P2"]], projects["beta"]
        ),
        # collected status + Arctis + Alpha
        "g_collected": make_grid(user, "g_collected", [labels["To Be Collected"], labels["Arctis"]], projects["alpha"]),
        # milled, no microscope, no project
        "g_milled": make_grid(user, "g_milled", [labels["To Be Milled"]]),
        # trashed grid with a status label — should never appear
        "g_trashed": make_grid(user, "g_trashed", [labels["TBS"]], trashed=True),
        # non-trashed grid without any status label — should never appear
        "g_nostatus": make_grid(user, "g_nostatus", [labels["Arctis"]], projects["alpha"]),
    }


def result_names(response):
    return {row["grid"]["name"] for row in response.json()["result"]}


@pytest.mark.django_db
class TestScreeningList:
    def test_base_excludes_trashed_and_unlabeled(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(SCREENING_URL, q([{"category": "pageSize", "value": 50}]))
        assert resp.status_code == 200
        names = result_names(resp)
        assert names == {"g_tbs", "g_long", "g_collected", "g_milled"}
        assert "g_trashed" not in names
        assert "g_nostatus" not in names

    def test_status_filter_matches_both_forms(self, client, user, screening_grids):
        """Selecting the long display name matches both short (TBS) and long grids."""
        client.force_login(user)
        resp = client.get(
            SCREENING_URL,
            q([{"category": "screeningStatus", "value": ["To Be Screened"]}, {"category": "pageSize", "value": 50}]),
        )
        assert result_names(resp) == {"g_tbs", "g_long"}

    def test_microscope_filter(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(
            SCREENING_URL,
            q([{"category": "microscope", "value": ["Arctis"]}, {"category": "pageSize", "value": 50}]),
        )
        assert result_names(resp) == {"g_tbs", "g_collected"}

    def test_project_filter(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(
            SCREENING_URL,
            q([{"category": "project", "value": ["Alpha"]}, {"category": "pageSize", "value": 50}]),
        )
        assert result_names(resp) == {"g_tbs", "g_collected"}

    def test_categories_combine_with_and(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(
            SCREENING_URL,
            q(
                [
                    {"category": "screeningStatus", "value": ["To Be Screened"]},
                    {"category": "microscope", "value": ["Arctis"]},
                    {"category": "pageSize", "value": 50},
                ]
            ),
        )
        # Only g_tbs has both a "screened" status AND Arctis.
        assert result_names(resp) == {"g_tbs"}
        assert resp.json()["pagination"]["totalResults"] == 1


@pytest.mark.django_db
class TestScreeningFilterlist:
    def test_returns_all_categories(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(FILTERLIST_URL)
        assert resp.status_code == 200
        filters = resp.json()["filters"]
        assert set(filters.keys()) == {"screeningStatus", "microscope", "priority", "project"}

    def test_status_counts(self, client, user, screening_grids):
        client.force_login(user)
        filters = client.get(FILTERLIST_URL).json()["filters"]
        status_counts = {opt["name"]: opt["count"] for opt in filters["screeningStatus"]}
        # g_tbs (short) + g_long (long) both count toward "To Be Screened"
        assert status_counts["To Be Screened"] == 2
        assert status_counts["To Be Collected"] == 1
        assert status_counts["To Be Milled"] == 1

    def test_microscope_uses_display_names(self, client, user, screening_grids):
        client.force_login(user)
        filters = client.get(FILTERLIST_URL).json()["filters"]
        micro_counts = {opt["name"]: opt["count"] for opt in filters["microscope"]}
        assert micro_counts == {"Arctis": 2, "Krios 1": 1}

    def test_project_counts(self, client, user, screening_grids):
        client.force_login(user)
        filters = client.get(FILTERLIST_URL).json()["filters"]
        project_counts = {opt["name"]: opt["count"] for opt in filters["project"]}
        # g_nostatus is on Alpha but has no status label, so it is excluded.
        assert project_counts == {"Alpha": 2, "Beta": 1}

    def test_selected_flag_reflects_query(self, client, user, screening_grids):
        client.force_login(user)
        resp = client.get(FILTERLIST_URL, q([{"category": "microscope", "value": ["Arctis"]}]))
        micro = {opt["name"]: opt["selected"] for opt in resp.json()["filters"]["microscope"]}
        assert micro["Arctis"] is True
        assert micro["Krios 1"] is False
