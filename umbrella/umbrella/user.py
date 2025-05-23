from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def get_user_info(request):
    """
    Returns the current user's ID and username.
    """
    return JsonResponse({
        'id': str(request.user.id),
        'username': request.user.username,
    })
