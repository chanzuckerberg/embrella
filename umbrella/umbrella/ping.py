from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse


@login_not_required
def ping(request):
    """Unauthenticated liveness probe"""
    return JsonResponse({"message": "pong"})
