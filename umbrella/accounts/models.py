from django.conf import settings
from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"

    def __str__(self):
        return f"Profile({self.user.username})"


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
