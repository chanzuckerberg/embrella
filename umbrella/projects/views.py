import json

from django.shortcuts import render
from django.core.serializers import serialize
from django.http import JsonResponse
from .models import Project

def index(request):
    project_list = Project.objects.all()
    context = {
                'projects':project_list,
    }
    return render(request, "projects/index.html", context)

def getproject(request):
    if not request.GET.get('valid', 'true') == 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    project_list = Project.objects.all()
    serialized_projects = serialize('json', project_list)
    projects_data = json.loads(serialized_projects)
    return JsonResponse(projects_data, safe=False)