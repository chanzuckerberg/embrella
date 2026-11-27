"""Bots log work for a person: ``user`` is the person, history keeps the bot."""

from http import HTTPStatus

import pytest
from cryo_grids.models import CryoGrid

from accounts.scopes import Scope
from accounts.tests.helpers import bearer_client, make_token

GRIDS = "/cryo_grids/v1/grids/"
TIMELINE = "/timeline/v1/grids/{}/"


def _create(client, test_grid, **extra):
    body = {
        "name": "grid2",
        "freezing_session": test_grid.freezing_session_id,
        "grid_box": test_grid.grid_box_id,
        "position_in_box": 2,
        **extra,
    }
    return client.post(GRIDS, body, content_type="application/json")


@pytest.mark.django_db
class TestOnBehalf:
    def test_user_required(self, owner, bot, test_grid):
        response = _create(bearer_client(make_token(owner, bot, Scope.WRITE)), test_grid)
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_user_must_be_person(self, owner, bot, test_grid):
        response = _create(bearer_client(make_token(owner, bot, Scope.WRITE)), test_grid, user=bot.id)
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_logged_via_bot(self, owner, bot, test_grid):
        response = _create(bearer_client(make_token(owner, bot, Scope.WRITE)), test_grid, user=owner.id)
        assert response.status_code == HTTPStatus.CREATED, response.content

        grid = CryoGrid.objects.get(name="grid2")
        assert grid.user == owner
        assert grid.history.earliest().history_user == bot

        entries = bearer_client(make_token(owner, bot)).get(TIMELINE.format(grid.id)).json()
        assert entries[-1]["user"] == "alice via bot-hydra-1"
