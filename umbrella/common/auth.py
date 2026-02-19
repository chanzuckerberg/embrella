from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication subclass that doesn't enforce CSRF checks.
    Use this for API endpoints that handle CSRF validation separately or don't require it.
    """

    def enforce_csrf(self, request):
        return  # Skip CSRF check
