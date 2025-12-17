from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def custom_page(request):
    """View for the custom dashboard page"""
    context = {
        'git_hash': settings.GIT_HASH,
        'git_branch': settings.GIT_BRANCH,
        'start_time': settings.START_TIME,
    }
    return render(request, 'customs/custom_page.html', context)


def user_guide_view(request):
    return render(request, "customs/user_guide.html")
