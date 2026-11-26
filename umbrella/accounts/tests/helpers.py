from django.test import Client

from accounts.scopes import Scope
from accounts.tokens import create_token


def make_token(owner, bot, *scopes, **kwargs) -> str:
    """Raw token for ``bot``, read-only unless ``scopes`` are given."""
    _, raw = create_token(owner, bot, "t", scopes or [Scope.READ], **kwargs)
    return raw


def bearer_client(raw) -> Client:
    # enforce_csrf_checks: prove tokens skip CSRF instead of the test client doing it
    return Client(enforce_csrf_checks=True, HTTP_AUTHORIZATION=f"Bearer {raw}")
