import json

import pytest
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

GRIDS_URL = "/cryo_grids/v1/grids/"


def _grid_ids(client, username):
    q = json.dumps([{"category": "user", "value": [username]}])
    return {r["grid"]["id"] for r in client.get(GRIDS_URL, {"q": q}).json()["result"]}


@pytest.fixture
def email_grid(test_grid):
    # Usernames are often emails; suggestions send only the local part.
    test_grid.user = User.objects.create_user(username="ddong@example.org")
    test_grid.save()
    return test_grid


def test_user_filter_matches_exact_username(logged_in_client, test_grid):
    assert _grid_ids(logged_in_client, test_grid.user.username) == {test_grid.pk}


def test_user_filter_rejects_substring(logged_in_client, test_grid):
    assert _grid_ids(logged_in_client, test_grid.user.username[:4]) == set()


def test_user_filter_matches_email_local_part(logged_in_client, email_grid):
    assert _grid_ids(logged_in_client, "ddong") == {email_grid.pk}


def test_user_filter_matches_full_email(logged_in_client, email_grid):
    assert _grid_ids(logged_in_client, "ddong@example.org") == {email_grid.pk}


def test_user_filter_rejects_local_part_prefix(logged_in_client, email_grid):
    assert _grid_ids(logged_in_client, "ddo") == set()
