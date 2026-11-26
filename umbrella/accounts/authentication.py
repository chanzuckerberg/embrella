"""Password backends that refuse bots."""

from allauth.account.auth_backends import AuthenticationBackend
from django.contrib.auth.backends import ModelBackend

from .bots import is_bot


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
