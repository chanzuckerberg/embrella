"""API tokens for bots: ``emb_`` + 40 hex chars, stored as SHA-256.

create_token(...)  →  (row, "emb_3f9a…")   raw value shown once
authenticate(raw)  →  row | None           expiry · audience · bot + owner active
"""

import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

from .bots import is_bot, is_usable
from .models import APIToken
from .scopes import EMBRELLA_AUDIENCE, grantable_scopes

TOKEN_PREFIX = "emb_"
TOKEN_HEX_BYTES = 20

# Throttle last_used_at writes
LAST_USED_RESOLUTION = timedelta(minutes=1)


class TokenError(ValueError):
    pass


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_token(creator, owner, name: str, scopes, expires_at=None) -> tuple[APIToken, str]:
    if not is_bot(owner):
        raise TokenError("Tokens belong to bots only.")

    unknown = set(scopes) - set(grantable_scopes())
    if unknown:
        raise TokenError(f"Unknown scopes: {sorted(unknown)}")

    raw = TOKEN_PREFIX + secrets.token_hex(TOKEN_HEX_BYTES)
    token = APIToken.objects.create(
        owner=owner,
        created_by=creator,
        name=name,
        token_sha256=_digest(raw),
        scopes=list(scopes),
        expires_at=expires_at,
    )
    return token, raw


def authenticate(raw: str) -> APIToken | None:
    if not raw.startswith(TOKEN_PREFIX):
        return None

    token = APIToken.objects.select_related("owner__profile__bot_owner").filter(token_sha256=_digest(raw)).first()
    if token is None:
        return None

    now = timezone.now()
    if token.expires_at and token.expires_at <= now:
        return None
    if token.audience != EMBRELLA_AUDIENCE:
        return None
    if not is_usable(token.owner):
        return None

    _touch(token, now)
    return token


def _touch(token: APIToken, now) -> None:
    if token.last_used_at and now - token.last_used_at < LAST_USED_RESOLUTION:
        return
    APIToken.objects.filter(pk=token.pk).update(last_used_at=now)
    token.last_used_at = now


def describe(token: APIToken) -> dict:
    """Payload for /api/tokens/self."""
    owner = token.owner
    return {
        "owner": {
            "id": owner.id,
            "username": owner.username,
            "is_bot": is_bot(owner),
            "bot_owner": owner.profile.bot_owner.username if is_bot(owner) else None,
        },
        "name": token.name,
        "scopes": token.scopes,
        "audience": token.audience,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
    }
