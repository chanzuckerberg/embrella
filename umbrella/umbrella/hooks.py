"""
Authentication hooks for the Umbrella project.

Contains callback functions for Google SSO authentication flow, including
pre-login callbacks for user permission management.
"""
from django.contrib import messages
from loguru import logger


def pre_login_callback(user, request):
    """Callback function called before user is logged in."""
    messages.info(request, f"Running Pre-Login callback for user: {user}.")
    if not user.is_superuser or not user.is_staff:
        logger.info(f"Adding SuperUser status to email: {user.email}")
        user.is_superuser = True
        user.is_staff = True
        user.save()
