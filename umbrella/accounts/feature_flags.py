"""Feature-flag lookup: per-user override wins, otherwise the system-wide flag.
Resolving ``flag`` for a user:
  - an explicit per-user value in ``Profile.feature_flags`` wins (on OR off), else
  - fall back to whether the global ``SystemFeatureFlag`` is enabled.
"""

from .models import Profile, SystemFeatureFlag


def is_feature_enabled(user, flag: str) -> bool:
    """Return whether ``flag`` is enabled for ``user`` (per-user override wins)."""
    # Authenticated users may have an explicit override that takes precedence.
    if getattr(user, "is_authenticated", False):
        try:
            overrides = user.profile.feature_flags
            if flag in overrides:
                return bool(overrides[flag])
        except Profile.DoesNotExist:
            pass

    return SystemFeatureFlag.objects.filter(name=flag, enabled=True).exists()


def enabled_flags_for(user) -> list[str]:
    """All flags enabled for ``user`` — system-on flags with per-user overrides applied.
    An explicit per-user override wins: it can add a flag or remove a system-on one.
    Used by the /user endpoint so the frontend knows which features to show.
    """
    flags = set(
        SystemFeatureFlag.objects.filter(enabled=True).values_list("name", flat=True)
    )
    if getattr(user, "is_authenticated", False):
        try:
            for name, on in user.profile.feature_flags.items():
                flags.add(name) if on else flags.discard(name)
        except Profile.DoesNotExist:
            pass
    return sorted(flags)
