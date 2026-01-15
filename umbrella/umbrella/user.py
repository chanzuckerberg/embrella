from django.http import JsonResponse


def get_user_info(request):
    """
    Returns the current user's ID and username.
    Returns 401 if not authenticated (allows frontend to handle redirect).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    return JsonResponse({
        'id': str(request.user.id),
        'username': request.user.username,
    })
