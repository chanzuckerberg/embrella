"""
Custom views for umbrella app.
"""
from django.contrib import admin
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from loguru import logger

from django_google_sso import views as google_sso_views


def _get_next_url(request):
    """Extract the next URL from query params or HTTP_REFERER."""
    next_url = request.GET.get('next', '')
    if not next_url:
        referrer = request.META.get('HTTP_REFERER', '')
        next_url = referrer if referrer else '/'
    return next_url


def custom_login_view(request):
    """
    Login view that shows both a username/password form and a Google SSO button.

    Stores the full next URL (including host) in the session so cross-origin
    redirects back to the frontend (e.g., localhost:3000) work after auth.
    """
    next_url = _get_next_url(request)
    request.session['google_sso_next_url'] = next_url

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            redirect_url = request.session.pop('google_sso_next_url', '/')
            return HttpResponseRedirect(redirect_url)
    else:
        form = AuthenticationForm(request)

    # Render the admin login template (django-google-sso's google_sso/login.html
    # extends admin/login.html and adds the SSO button alongside the form)
    context = {
        'form': form,
        'next': next_url,
        **admin.site.each_context(request),
    }
    return render(request, 'google_sso/login.html', context)


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
