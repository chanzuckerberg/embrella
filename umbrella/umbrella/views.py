"""
Custom views for umbrella app.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponseRedirect
from urllib.parse import urlencode
from loguru import logger
from django_google_sso import views as google_sso_views


def custom_login_view(request):
    """
    Custom login view that redirects to Google SSO with proper next parameter.

    Uses HTTP_REFERER to preserve the frontend URL across different ports
    (e.g., http://localhost:3000/workflows/launch) instead of relative paths.

    Stores the next URL in session so it persists through OAuth redirects.
    """
    # Get the next URL from query params or HTTP_REFERER
    next_url = request.GET.get('next', '')

    if not next_url:
        # Use HTTP_REFERER to get the full URL the user came from
        # This preserves frontend URLs like http://localhost:3000/workflows/launch
        referrer = request.META.get('HTTP_REFERER', '')
        next_url = referrer if referrer else '/'

    # Store next URL in session so it persists through OAuth redirects
    request.session['google_sso_next_url'] = next_url

    # Redirect to Google SSO login with the next parameter
    google_sso_url = reverse('django_google_sso:oauth_start_login')
    redirect_url = f'{google_sso_url}?{urlencode({"next": next_url})}'

    return redirect(redirect_url)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def custom_logout_view(request):
    """
    Custom logout view that accepts both GET and POST requests.

    Logs out the user and redirects to the root page.
    """
    logout(request)
    next_url = request.GET.get('next', '/')
    return redirect(next_url)


@require_http_methods(["GET"])
def custom_google_sso_callback(request: HttpRequest) -> HttpResponseRedirect:
    """
    Custom callback for Google SSO that preserves the full frontend URL.

    Wraps the django-google-sso callback and redirects to the full URL
    stored in session (including scheme and host) instead of just the path.
    This allows redirecting back to localhost:3000 (frontend) instead of
    localhost:8000 (backend) after authentication.
    """
    # Call the original django-google-sso callback
    response = google_sso_views.callback(request)

    # Check if we have a stored frontend URL in session
    frontend_url = request.session.pop('google_sso_next_url', None)

    if frontend_url and isinstance(response, HttpResponseRedirect):
        # Redirect to the frontend URL instead of the backend path
        logger.info(f"Custom callback: redirecting to frontend URL: {frontend_url}")
        return HttpResponseRedirect(frontend_url)

    return response
