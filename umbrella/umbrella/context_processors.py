from django.conf import settings


def demo_flags(request):
    """Expose demo-mode flags to templates (e.g. to hide SSO on the locked demo)."""
    return {"EMBRELLA_DISABLE_SIGNUP": getattr(settings, "EMBRELLA_DISABLE_SIGNUP", False)}
