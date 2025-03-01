from django.shortcuts import render
from django.contrib.auth.decorators import login_required
@login_required
def custom_page(request):
    return render(request, 'customs/custom_page.html')


def user_guide_view(request):
    return render(request, "customs/user_guide.html")


def chatbot_view(request):
    return render(request, "customs/chatbot.html")
