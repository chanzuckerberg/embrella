"""Bot users: ``auth.User`` rows owned by a human (``Profile.bot_owner``).

A bot authenticates only with an API token, never a password or SSO.
"""

from enum import Enum

from django.contrib.auth.models import User
from django.db import transaction

BOT_PREFIX = "bot-"


class BotState(Enum):
    ACTIVE = True
    DISABLED = False


class BotError(ValueError):
    pass


def is_bot(user) -> bool:
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_bot)


@transaction.atomic
def create_bot(owner, username: str, name: str = "") -> User:
    if is_bot(owner) or not owner.is_active:
        raise BotError("A bot's owner must be an active human.")

    if not username.startswith(BOT_PREFIX):
        raise BotError(f"Bot usernames start with '{BOT_PREFIX}'.")

    # Never staff/superuser; no email, so no notifications or SSO match
    bot = User(username=username, first_name=name)
    bot.set_unusable_password()
    bot.save()

    # The post_save signal created the profile
    bot.profile.bot_owner = owner
    bot.profile.save(update_fields=["bot_owner", "updated_at"])
    return bot


def set_active(bot, state: BotState) -> None:
    bot.is_active = state.value
    bot.save(update_fields=["is_active"])


def delete_bot(bot) -> None:
    bot.delete()


def is_usable(user) -> bool:
    """A bot works only while it and its owner are both active."""
    if not user.is_active:
        return False
    if not is_bot(user):
        return True
    return user.profile.bot_owner.is_active
