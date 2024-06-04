from django.shortcuts import render
from django.contrib.auth.decorators import login_required
@login_required
def custom_page(request):
    return render(request, 'customs/custom_page.html')