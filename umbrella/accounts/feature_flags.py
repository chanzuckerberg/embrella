"""Feature-flag lookup: combines the system-wide flag with per-user overrides.
A feature is ON for a user when EITHER:
  - the global ``SystemFeatureFlag`` is enabled for everyone, OR
  - the user enabled it in ``Profile.feature_flags``.
"""

from .models import Profile, SystemFeatureFlag


def is_feature_enabled(user, flag: str) -> bool:
    """Return whether ``flag`` is enabled for ``user`` (global OR per-user override)."""
    if SystemFeatureFlag.objects.filter(name=flag, enabled=True).exists():
        return True

    # Anonymous users have no overrides.
    if not getattr(user, "is_authenticated", False):
        return False

    # Per-user override.
    try:
        return bool(user.profile.feature_flags.get(flag))
    except Profile.DoesNotExist:
        return False


def enabled_flags_for(user) -> list[str]:
    """All flags enabled for ``user`` — globally-on flags plus their profile overrides.
    Used by the /user endpoint so the frontend knows which features to show.
    """
    flags = set(
        SystemFeatureFlag.objects.filter(enabled=True).values_list("name", flat=True)
    )
    if getattr(user, "is_authenticated", False):
        try:
            flags |= {name for name, on in user.profile.feature_flags.items() if on}
        except Profile.DoesNotExist:
            pass
    return sorted(flags)
