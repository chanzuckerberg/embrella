"""
API views for cryo-grid management.

Contains API endpoints for querying and managing cryo grids by user and project.
"""

import logging

from django.db.models import BooleanField, Case, F, Value, When
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view

from cryo_grids.models import CryoGrid

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns cryo grids for a specific user with metadata and is_default flag.",
    parameters=[
        OpenApiParameter(name="user_id", required=False, type=str, description="User ID to filter cryo grids"),
    ],
    responses={200: "List of cryo grids"},
)
@api_view(["GET"])
def get_grids_by_user(request):
    """
    Get cryo grids filtered by user ID with metadata.

    Query Parameters:
        user_id (optional): Filter grids by user ID

    Returns:
        JSON list of grids with project_name, username, is_default flag, timestamps,
        and display_name including location info (puck, slot, position)
    """
    user_id = request.GET.get("user_id")

    # Annotate each grid with an is_default flag based on the grid name.
    queryset = CryoGrid.objects.select_related(
        "intended_project",
        "user",
        "grid_box",
        "grid_box__puck",
    ).annotate(
        project_name=F("intended_project__name"),
        username=F("user__username"),
        is_default=Case(
            When(name__icontains="default grid", then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Order by create_on in descending order (newest first)
    queryset = queryset.order_by("-create_on")

    # Build response with display_name including location info
    grids_data = []
    for grid in queryset:
        # Build display_name with location info
        location_parts = []
        if grid.grid_box and grid.grid_box.puck:
            location_parts.append(f"Puck: CZII-0{grid.grid_box.puck.name}")
        if grid.grid_box:
            location_parts.append(f"Slot: {grid.grid_box.position_in_puck or '?'}")
        if grid.position_in_box:
            location_parts.append(f"Position: {grid.position_in_box}")

        if location_parts:
            display_name = f"{grid.name} ({', '.join(location_parts)})"
        else:
            display_name = grid.name

        grids_data.append(
            {
                "id": grid.id,
                "name": grid.name,
                "display_name": display_name,
                "project_name": grid.intended_project.name if grid.intended_project else None,
                "username": grid.user.username if grid.user else None,
                "is_default": "default grid" in grid.name.lower() if grid.name else False,
                "create_on": grid.create_on.isoformat() if grid.create_on else None,
            }
        )

    return JsonResponse(grids_data, safe=False)
