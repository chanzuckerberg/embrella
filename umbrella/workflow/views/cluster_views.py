"""Cluster listing for frontend cluster pickers."""

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from processes.services.cluster_resolver import active_clusters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@extend_schema(
    summary="List active clusters",
    description="Active compute clusters, sorted by name. Exactly one is flagged `is_default`.",
    responses={
        200: OpenApiResponse(
            description="Active clusters",
            response={
                "type": "object",
                "properties": {
                    "clusters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cluster_id": {"type": "string"},
                                "name": {"type": "string"},
                                "is_default": {"type": "boolean"},
                            },
                            "required": ["cluster_id", "name", "is_default"],
                        },
                    },
                },
                "required": ["clusters"],
            },
            examples=[
                OpenApiExample(
                    "Two clusters",
                    value={
                        "clusters": [
                            {"cluster_id": "hpc-a", "name": "HPC A", "is_default": True},
                            {"cluster_id": "hpc-b", "name": "HPC B", "is_default": False},
                        ],
                    },
                ),
            ],
        ),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_clusters(request):
    return JsonResponse({"clusters": active_clusters()})
