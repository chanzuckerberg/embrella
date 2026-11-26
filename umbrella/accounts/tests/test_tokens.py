"""API tokens and the token middleware."""

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import get_resolver
from django.utils import timezone

from accounts.bots import BotState, set_active
from accounts.models import APIToken
from accounts.scopes import DENIED_VIEWS, DENIED_WRITES, Scope
from accounts.tests.helpers import bearer_client, make_token
from accounts.tokens import TOKEN_PREFIX, TokenError, authenticate, create_token

GRIDS = "/cryo_grids/v1/grids/"


@pytest.mark.django_db
class TestTokens:
    def test_hash_only(self, owner, bot):
        raw = make_token(owner, bot)
        assert raw.startswith(TOKEN_PREFIX)
        assert not APIToken.objects.filter(token_sha256=raw).exists()
        assert authenticate(raw).owner == bot

    def test_bots_only(self, owner):
        with pytest.raises(TokenError):
            create_token(owner, owner, "t", [Scope.READ])

    def test_unknown_scope(self, owner, bot):
        with pytest.raises(TokenError):
            create_token(owner, bot, "t", ["embrella:everything"])

    def test_extra_scopes(self, owner, bot, settings):
        settings.TOKEN_EXTRA_SCOPES = ["ai:agents:report"]
        create_token(owner, bot, "t", ["ai:agents:report"])

    def test_expired(self, owner, bot):
        raw = make_token(owner, bot, expires_at=timezone.now() - timedelta(seconds=1))
        assert authenticate(raw) is None

    def test_no_expiry(self, owner, bot):
        assert authenticate(make_token(owner, bot)) is not None

    def test_wrong_audience(self, owner, bot):
        raw = make_token(owner, bot)
        APIToken.objects.update(audience="other")
        assert authenticate(raw) is None

    def test_disabled_bot_or_owner(self, owner, bot):
        raw = make_token(owner, bot)
        set_active(bot, BotState.DISABLED)
        assert authenticate(raw) is None

        set_active(bot, BotState.ACTIVE)
        owner.is_active = False
        owner.save()
        assert authenticate(raw) is None

    def test_self(self, owner, bot):
        body = bearer_client(make_token(owner, bot)).get("/api/tokens/self").json()
        assert body["owner"] == {"id": bot.id, "username": bot.username, "is_bot": True, "bot_owner": "alice"}
        assert body["scopes"] == [Scope.READ]


@pytest.mark.django_db
class TestMiddleware:
    def test_bad_token_401(self):
        assert bearer_client(TOKEN_PREFIX + "0" * 40).get(GRIDS).status_code == HTTPStatus.UNAUTHORIZED

    def test_read(self, owner, bot, test_grid):
        client = bearer_client(make_token(owner, bot))
        assert client.get(f"{GRIDS}{test_grid.id}/").status_code == HTTPStatus.OK
        assert client.patch(f"{GRIDS}{test_grid.id}/").status_code == HTTPStatus.FORBIDDEN

    def test_write_skips_csrf(self, owner, bot, test_grid):
        client = bearer_client(make_token(owner, bot, Scope.WRITE))
        response = client.patch(f"{GRIDS}{test_grid.id}/", {"notes": "hi"}, content_type="application/json")
        assert response.status_code == HTTPStatus.OK

    def test_session_still_needs_csrf(self, owner, test_grid):
        client = Client(enforce_csrf_checks=True)
        client.force_login(owner)
        response = client.patch(f"{GRIDS}{test_grid.id}/", {"notes": "hi"}, content_type="application/json")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_plain_view_no_redirect(self, owner, bot):
        # tem/v1 form options is a plain Django view behind LoginRequiredMiddleware
        response = bearer_client(make_token(owner, bot)).get("/tem/v1/sessions/form-options/")
        assert response.status_code != HTTPStatus.FOUND

    def test_denied_routes(self, owner, bot):
        client = bearer_client(make_token(owner, bot, Scope.WRITE))
        assert client.get("/admin/").status_code == HTTPStatus.FORBIDDEN
        assert client.get("/accounts/login/").status_code == HTTPStatus.FORBIDDEN
        assert client.post("/workflow/v1/ssh/setup_key/").status_code == HTTPStatus.FORBIDDEN


def _names(patterns, prefix=""):
    for p in patterns:
        if hasattr(p, "url_patterns"):
            ns = f"{prefix}{p.namespace}:" if p.namespace else prefix
            yield from _names(p.url_patterns, ns)
        elif p.name:
            yield prefix + p.name


def test_denied_names_exist():
    """A renamed route must not silently drop out of the deny list."""
    names = set(_names(get_resolver().url_patterns))
    assert names >= (DENIED_VIEWS | DENIED_WRITES)


@pytest.mark.django_db
def test_admin_add_token_shows_raw_once(staff, owner, bot):
    body = {"owner": bot.id, "name": "hydra", "scopes": [Scope.READ]}
    response = staff.post("/admin/accounts/apitoken/add/", body)
    assert response.status_code == HTTPStatus.OK

    raw = response.context["raw"]
    assert raw in response.content.decode()
    assert authenticate(raw).owner == bot

    token = APIToken.objects.get()
    assert token.created_by == owner
    assert staff.get(f"/admin/accounts/apitoken/{token.id}/change/").status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_self_needs_token(staff):
    assert staff.get("/api/tokens/self").status_code == HTTPStatus.UNAUTHORIZED


def test_basic_auth_rejected(db):
    client = Client(HTTP_AUTHORIZATION="Basic YWxpY2U6cHc=")  # alice:pw
    assert client.get(GRIDS, HTTP_ACCEPT="application/json").status_code == HTTPStatus.UNAUTHORIZED
