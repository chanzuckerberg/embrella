"""Bot users: creation rules, login guards, cluster block, admin."""

from http import HTTPStatus

import pytest
from django.contrib.auth import authenticate as password_login
from django.contrib.auth.models import User

from accounts.bots import BotError, create_bot
from accounts.cluster_usernames import MissingClusterCredentialsError, resolve_cluster_username


@pytest.mark.django_db
class TestBots:
    def test_create(self, owner, bot):
        assert bot.profile.bot_owner == owner
        assert not bot.has_usable_password()
        assert not bot.is_staff

    def test_prefix_required(self, owner):
        with pytest.raises(BotError):
            create_bot(owner, "hydra", "")

    def test_bot_cannot_own_bot(self, bot):
        with pytest.raises(BotError):
            create_bot(bot, "bot-child", "")

    def test_password_login_rejected(self, bot):
        bot.set_password("pw")
        bot.save()
        assert password_login(username=bot.username, password="pw") is None

    def test_no_cluster_jobs(self, bot):
        with pytest.raises(MissingClusterCredentialsError):
            resolve_cluster_username(bot, "any-cluster")

    def test_hidden_from_user_picker(self, owner, bot, client):
        client.force_login(owner)
        names = [u["username"] for u in client.get("/api/list/all/users/").json()["users"]]
        assert bot.username not in names


@pytest.mark.django_db
def test_admin_add_bot(staff, owner):
    body = {"username": "bot-admin", "first_name": "Admin bot", "owner": owner.id}
    response = staff.post("/admin/accounts/bot/add/", body)
    assert response.status_code == HTTPStatus.FOUND, response.content

    bot = User.objects.get(username="bot-admin")
    assert bot.profile.bot_owner == owner
    assert staff.get("/admin/accounts/bot/").status_code == HTTPStatus.OK


@pytest.mark.django_db
@pytest.mark.parametrize("typed", ["hydra-1", "bot-hydra-1"])
def test_admin_prepends_prefix(staff, owner, typed):
    response = staff.post("/admin/accounts/bot/add/", {"username": typed, "first_name": "", "owner": owner.id})
    assert response.status_code == HTTPStatus.FOUND, response.content
    assert User.objects.filter(username="bot-hydra-1").exists()
