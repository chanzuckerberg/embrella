import json

from cryo_grids.serializers import ProjectSerializer
from django.core.serializers import serialize
from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Project


@extend_schema(
    methods=["GET"],
    description="Returns all projects as serialized JSON. Requires ?valid=true.",
    parameters=[
        OpenApiParameter(
            name="valid",
            required=True,
            type=bool,
            description="Must be true to get project list",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
def getproject(request):
    if request.GET.get("valid", "true") != "true":
        return JsonResponse({"error": "Invalid request"}, status=400)
    project_list = Project.objects.all()
    serialized_projects = serialize("json", project_list)
    projects_data = json.loads(serialized_projects)
    return JsonResponse(projects_data, safe=False)


@extend_schema(
    methods=["POST"],
    description="Create a new project.",
    request=ProjectSerializer,
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_project(request):
    """
    Create a new project.

    Request Body:
    {
        "name": "TRD06",
        "description": "Project description",  // optional
        "project_leader": 1,  // optional, user ID
        "documentation_space": 2  // optional, ExternalResource ID
    }
    """
    try:
        serializer = ProjectSerializer(data=request.data)

        if serializer.is_valid():
            project = serializer.save()
            return Response(
                {
                    "message": "Project created successfully",
                    "project": ProjectSerializer(project).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "error": "Validation failed",
                    "detail": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        return Response(
            {
                "error": "Failed to create project",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
