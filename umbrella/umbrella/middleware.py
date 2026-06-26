"""
Custom middleware for the Umbrella project.

Contains middleware classes for handling authentication redirects and custom workflows.
"""

import re
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from umbrella_logger import logger

# Session key used to bridge cross-origin redirects back to the frontend
# (e.g. localhost:3000) after login/logout. Consumed by umbrella.adapters.
# This module is the single source of truth; adapters imports it from here.
SESSION_NEXT_URL_KEY = "auth_next_url"


# Path portion of LOGIN_URL (e.g. '/accounts/login/'). LOGIN_URL is static, so
# compute it once at import rather than per request.
LOGIN_PATH = urlparse(settings.LOGIN_URL).path


def _is_login_redirect(location):
    """True if a redirect Location points at the login page."""
    return bool(location) and LOGIN_PATH in location


class PathExemptLoginRequiredMiddleware(LoginRequiredMiddleware):
    """
    Django 5.2's built-in LoginRequiredMiddleware makes every view login-required
    and only supports opting out per-view via @login_not_required. This subclass
    restores the path-based ignore list we relied on previously: requests whose
    path matches LOGIN_REQUIRED_IGNORE_PATHS skip the login requirement.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self._exempt = [re.compile(p) for p in getattr(settings, "LOGIN_REQUIRED_IGNORE_PATHS", [])]

    def process_view(self, request, view_func, view_args, view_kwargs):
        if any(pattern.match(request.path) for pattern in self._exempt):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)


class APIAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to return 401 for API requests instead of redirecting to login.

    When an AJAX/API request requires authentication, return 401 instead of
    redirecting. This allows the frontend to handle the authentication flow.

    Only applies to fetch/AJAX requests, not browser navigation.
    """

    def process_response(self, request, response):
        # Log the response type for the POST request to debug
        if request.path == "/workflow/v1/execution/preview/":
            logger.info(
                f"APIAuthenticationMiddleware: Processing response for {request.path}: type={type(response).__name__}, status={getattr(response, 'status_code', 'N/A')}"
            )

        # Log ALL redirects for debugging
        if isinstance(response, HttpResponseRedirect):
            location = response.get("Location", "")
            logger.info(f"APIAuthenticationMiddleware: Redirect detected for {request.path} -> {location}")

            # Check if redirecting to login
            if _is_login_redirect(location):
                # Log request details for debugging
                fetch_mode = request.META.get("HTTP_SEC_FETCH_MODE", "")
                fetch_dest = request.META.get("HTTP_SEC_FETCH_DEST", "")
                x_requested_with = request.META.get("HTTP_X_REQUESTED_WITH", "")
                content_type = request.META.get("CONTENT_TYPE", "")
                accept = request.META.get("HTTP_ACCEPT", "")

                logger.info(
                    f"Login redirect detected for {request.path}: "
                    f"Sec-Fetch-Mode={fetch_mode}, "
                    f"Sec-Fetch-Dest={fetch_dest}, "
                    f"X-Requested-With={x_requested_with}, "
                    f"Content-Type={content_type}, "
                    f"Accept={accept}"
                )

                # Check if this is a fetch/AJAX request using the Fetch API or XMLHttpRequest
                # The key indicator is the 'Sec-Fetch-Mode' header
                # 'cors' = cross-origin fetch, 'same-origin' = same-origin fetch, 'navigate' = browser navigation
                # We want to intercept both cors AND same-origin fetch requests
                is_fetch_request = fetch_mode in ("cors", "same-origin")

                # Also check for XMLHttpRequest
                is_ajax = x_requested_with == "XMLHttpRequest"

                # Also check Accept header - fetch requests typically accept application/json
                is_json_request = accept and "application/json" in accept

                # Only return 401 for actual fetch/AJAX, NOT for browser navigation
                if is_fetch_request or is_ajax or is_json_request:
                    # Return 401 instead of redirecting
                    from django.http import JsonResponse

                    logger.info(f"Returning 401 for fetch/AJAX request to {request.path}")

                    # Get the origin from the request
                    origin = request.META.get("HTTP_ORIGIN", "")

                    json_response = JsonResponse(
                        {"error": "Authentication required", "login_url": LOGIN_PATH}, status=401
                    )

                    # Add comprehensive CORS headers to allow frontend to read the 401 response
                    # This is critical - without these headers, the browser will block the response
                    if origin:
                        allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
                        if origin in allowed_origins:
                            json_response["Access-Control-Allow-Origin"] = origin
                            json_response["Access-Control-Allow-Credentials"] = "true"
                            json_response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                            json_response["Access-Control-Allow-Headers"] = (
                                "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with"
                            )
                            json_response["Access-Control-Expose-Headers"] = "Content-Type"
                            logger.info(f"Added CORS headers for origin: {origin}")
                        else:
                            logger.warning(f"Origin {origin} not in allowed origins: {allowed_origins}")
                    else:
                        logger.warning("No origin header in request")

                    return json_response

        return response


class FixLoginRedirectMiddleware(MiddlewareMixin):
    """
    Middleware to fix login redirects to use HTTP_REFERER instead of relative paths.

    When the login-required middleware redirects to /accounts/login/?next=/some/path,
    this middleware rewrites the next parameter to the full HTTP_REFERER URL to
    preserve the frontend URL across different ports (e.g., localhost:3000).

    On the way in, when the login page itself is requested, it stashes that full
    frontend URL in the session so umbrella.adapters can redirect back to it after
    a successful (cross-origin) login — allauth rejects cross-origin `next` params.
    """

    def process_request(self, request):
        # Capture the originating frontend URL when the login page loads, mirroring
        # the old custom_login_view: prefer ?next=, fall back to the referrer.
        if request.path == LOGIN_PATH:
            next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "") or "/"
            request.session[SESSION_NEXT_URL_KEY] = next_url

    def process_response(self, request, response):
        # Check if this is a redirect to the login page
        if isinstance(response, HttpResponseRedirect):
            location = response.get("Location", "")

            # Check if redirecting to login page with a next parameter
            if _is_login_redirect(location) and "next=" in location:
                # Get the HTTP_REFERER (full URL the user came from)
                referrer = request.META.get("HTTP_REFERER", "")

                if referrer:
                    # Parse the redirect URL
                    parsed = urlparse(location)
                    query_params = parse_qs(parsed.query)

                    # Replace the next parameter with the referrer
                    query_params["next"] = [referrer]

                    # Rebuild the URL
                    new_location = f"{parsed.path}?{urlencode(query_params, doseq=True)}"

                    logger.info(f"Fixed login redirect from {location} to {new_location} with next={referrer}")
                    response["Location"] = new_location

            # Add CORS headers to redirect responses for cross-origin requests
            origin = request.META.get("HTTP_ORIGIN", "")
            if origin and origin in getattr(settings, "CORS_ALLOWED_ORIGINS", []):
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"

        return response
