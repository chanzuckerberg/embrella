from accounts.feature_flags import enabled_flags_for
from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse


@login_not_required
def get_user_info(request):
    """
    Returns the current user's ID, username, staff status, and enabled feature flags.
    Returns 401 if not authenticated (allows frontend to handle redirect).
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    return JsonResponse(
        {
            "id": str(request.user.id),
            "username": request.user.username,
            "is_staff": request.user.is_staff,
            "feature_flags": enabled_flags_for(request.user),
        }
    )
