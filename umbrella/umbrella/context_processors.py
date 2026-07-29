from django.conf import settings


def auth_flags(request):
    """Expose auth flags to templates (e.g. to hide SSO when it isn't configured)."""
    return {"GOOGLE_SSO_ENABLED": getattr(settings, "GOOGLE_SSO_ENABLED", False)}
