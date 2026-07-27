from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render


@login_required
def custom_page(request):
    """View for the custom dashboard page"""
    context = {
        "git_hash": settings.GIT_HASH,
        "git_branch": settings.GIT_BRANCH,
        "start_time": settings.START_TIME,
    }
    return render(request, "customs/custom_page.html", context)


@login_required
def version_info(request):
    """API endpoint for version information"""
    return JsonResponse(
        {
            "git_hash": settings.GIT_HASH,
            "git_branch": settings.GIT_BRANCH,
            "start_time": settings.START_TIME,
        }
    )
