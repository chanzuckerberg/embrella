"""
django-allauth adapters for the Umbrella project.
- ``UmbrellaSocialAccountAdapter`` restricts SSO to allowed email domains
- ``UmbrellaAccountAdapter`` disables open local self-registration and preserves
  the cross-origin redirect bridge back to the frontend
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.http import url_has_allowed_host_and_scheme
from umbrella_logger import logger

from umbrella.middleware import SESSION_NEXT_URL_KEY


def _email_domain(email):
    return email.rsplit("@", 1)[-1].lower() if email and "@" in email else ""


def _is_allowed_redirect(request, url):
    """Whether ``url`` is a safe post-auth redirect target.

    The candidate ultimately comes from a user-controlled ``next`` param or
    Referer, so it must be validated to prevent open redirects. Two cases pass:

    1. Same-origin / relative URLs, validated by Django's host+scheme check.
    2. Absolute URLs whose origin is in ``CORS_ALLOWED_ORIGINS`` — the
       cross-origin frontend (e.g. http://localhost:3000) we deliberately
       bridge back to, which allauth's own safe-redirect check rejects.

    Everything else (``//evil.com``, ``https://evil.com``, or a lookalike like
    ``http://localhost:3000.evil.com``) is rejected.
    """
    if not url:
        return False
    allowed_hosts = {request.get_host(), *getattr(settings, "ALLOWED_HOSTS", [])}
    if url_has_allowed_host_and_scheme(url, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        return True
    # Require a path/origin boundary so a prefix can't be abused
    # (e.g. "http://localhost:3000.evil.com" must not match "http://localhost:3000").
    return any(
        url == origin or url.startswith(origin.rstrip("/") + "/")
        for origin in getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    )


class UmbrellaSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Restrict social login to allowed domains.
    Currently only support Google sign in"""

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email or sociallogin.account.extra_data.get("email", "")
        domain = _email_domain(email)
        allowed = getattr(settings, "SSO_ALLOWED_DOMAINS", [])
        if domain not in allowed:
            logger.warning(f"Rejected SSO login for disallowed domain: {email!r}")
            raise ImmediateHttpResponse(
                HttpResponseForbidden("Your email domain is not permitted to access this application.")
            )

    def is_open_for_signup(self, request, sociallogin):
        # Google sign-ups are allowed (domain-gated by pre_social_login above).
        return True


class UmbrellaAccountAdapter(DefaultAccountAdapter):
    """Disable local self-registration; redirect back to the frontend after auth."""

    def populate_username(self, request, user):
        # Default allauth picks the first non-empty of [first_name, last_name, ...],
        # so people end up as just their first name
        # Try "firstname.lastname"; allauth appends a numeric suffix
        # on collision. Falls back to the email local part, then the defaults.
        from allauth.account.utils import user_email, user_field, user_username

        first_name = (user_field(user, "first_name") or "").strip()
        last_name = (user_field(user, "last_name") or "").strip()
        email = user_email(user)
        username = user_username(user)
        candidates = []
        if first_name and last_name:
            candidates.append(f"{first_name}.{last_name}")
        candidates += [email, first_name, last_name, "unknown_user"]
        user_username(user, username or self.generate_unique_username(candidates))

    def is_open_for_signup(self, request):
        # No open local account registration — accounts come from Google SSO or
        # are created by an admin. (allauth would otherwise expose /accounts/signup/.)
        return False

    def get_login_redirect_url(self, request):
        # The full frontend URL was stashed in the session when the login page
        # loaded (see FixLoginRedirectMiddleware). allauth's safe-redirect check
        # rejects cross-origin `next` params, so we bridge it via the session.
        next_url = request.session.pop(SESSION_NEXT_URL_KEY, None)
        if _is_allowed_redirect(request, next_url):
            return next_url
        return super().get_login_redirect_url(request)

    def get_logout_redirect_url(self, request):
        # logout() flushes the session, so the session bridge can't be used here.
        # Honor an explicit ?next= only if it's a safe (same-origin or CORS-allowed) target.
        next_url = request.GET.get("next") or request.POST.get("next")
        if _is_allowed_redirect(request, next_url):
            return next_url
        return super().get_logout_redirect_url(request)
