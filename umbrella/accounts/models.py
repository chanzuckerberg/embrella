from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from .scopes import EMBRELLA_AUDIENCE


class Profile(models.Model):
    """Per-user identity and feature-flag settings adjacent to ``auth.User``."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    orcid_authenticated = models.CharField(
        max_length=19,
        blank=True,
        help_text="Verified ORCID iD for this account, set by the ORCID login flow.",
    )
    feature_flags = models.JSONField(default=dict, blank=True)
    # Set only for bots: the human accountable for it. NULL means a human.
    bot_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bots",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"

    def __str__(self):
        return f"Profile({self.user.username})"

    @property
    def is_bot(self) -> bool:
        return self.bot_owner_id is not None


class SystemFeatureFlag(models.Model):
    """Global feature flag, toggled in the admin.
    Default OFF. Per-user overrides live on ``Profile.feature_flags`` — see
    ``accounts.feature_flags.is_feature_enabled``: a feature is on for a user if
    the global flag is enabled OR the user has it enabled in their profile.
    """

    name = models.SlugField(max_length=100, unique=True, help_text="Flag key, e.g. 'deposition'.")
    enabled = models.BooleanField(default=False, help_text="On for everyone when True.")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "accounts"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}={'on' if self.enabled else 'off'}"


class UserClusterCredentials(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cluster_credentials",
    )
    cluster = models.ForeignKey("stores.Cluster", on_delete=models.CASCADE)
    username = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"
        db_table = "users_userclustercredentials"
        unique_together = ("user", "cluster")
        verbose_name_plural = "User cluster credentials"

    def __str__(self):
        return f"{self.user.username} @ {self.cluster_id} = {self.username}"


class Bot(User):
    """Proxy over users whose profile has a ``bot_owner``, i.e. bots."""

    class Meta:
        proxy = True
        app_label = "accounts"


class APIToken(models.Model):
    """Bearer token for a bot. Only the SHA-256 of the raw token is stored."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_api_tokens",
    )
    name = models.CharField(max_length=100)
    token_sha256 = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)

    # Service the token is for. Embrella only accepts its own; tokens it issues for other services
    # (e.g. an AI agent backend) get their audience, so a leaked one can't call Embrella's API.
    audience = models.CharField(max_length=64, default=EMBRELLA_AUDIENCE)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Empty means it never expires.")
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounts"
        verbose_name = "API token"

    def __str__(self):
        return f"{self.name} ({self.owner.username})"
