import json

from django.core.serializers import serialize
from django.http import JsonResponse
from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view

from .models import Project


def index(request):
    project_list = Project.objects.all()
    context = {
                'projects':project_list,
    }
    return render(request, "projects/index.html", context)

@extend_schema(
    methods=["GET"],
    description="Returns all projects as serialized JSON. Requires ?valid=true.",
    parameters=[
        OpenApiParameter(
            name='valid',
            required=True,
            type=bool,
            description='Must be true to get project list',
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
def getproject(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    project_list = Project.objects.all()
    serialized_projects = serialize('json', project_list)
    projects_data = json.loads(serialized_projects)
    return JsonResponse(projects_data, safe=False)
