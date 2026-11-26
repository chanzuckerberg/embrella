"""Auth hooks for bots: DRF reads the middleware's token; password backends refuse bots."""

from allauth.account.auth_backends import AuthenticationBackend
from django.contrib.auth.backends import ModelBackend
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication

from .bots import is_bot


class TokenFromMiddleware(BaseAuthentication):
    """The bot ``TokenAuthMiddleware`` already authenticated, if any."""

    def authenticate(self, request):
        token = getattr(request._request, "api_token", None)
        if token is None:
            return None
        return token.owner, token

    def authenticate_header(self, request):
        # Makes DRF answer unauthenticated requests 401, not 403
        return "Bearer"


class TokenScheme(OpenApiAuthenticationExtension):
    """Adds "Bearer" to the Swagger Authorize dialog (/api/docs), for trying tokens."""

    target_class = TokenFromMiddleware
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "description": "API token, e.g. emb_3f9a…"}


class HumansOnly:
    """Never log a bot in by password, even one set by hand.

    Checked at login only, not in ``get_user``, so session requests pay no extra query.
    """

    def authenticate(self, request, *args, **kwargs):
        user = super().authenticate(request, *args, **kwargs)
        return None if user is None or is_bot(user) else user


class HumanModelBackend(HumansOnly, ModelBackend):
    pass


class HumanAllauthBackend(HumansOnly, AuthenticationBackend):
    pass
