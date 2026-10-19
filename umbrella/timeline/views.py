from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from timeline.serializers import TimelineEntrySerializer
from timeline.services import grid_timeline

MOVE_EXAMPLE = {
    "at": "2026-02-03T14:05:00Z",
    "subject": "grid",
    "subject_id": 42,
    "kind": "moved",
    "summary": "Moved from BoxA #1 to BoxB #2",
    "user": "jdoe",
    "detail": {"reason": "moved", "changes": {"grid_box_id": [7, 9], "position_in_box": [1, 2]}},
}


class GridTimelineView(APIView):
    """
    GET /timeline/v1/grids/<grid_id>/

    Grid history: its own changes, labels, container moves, MSI sessions and proc runs.
    Served for trashed grids too.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="timeline_grid",
        summary="Grid timeline",
        description=(
            "Everything that happened to a grid, newest first: creation, edits, moves (including its box, "
            "puck, cane or dewar moving while it was inside), clipping, trashing, labels, MSI sessions and "
            "proc runs. Trashed and deleted grids keep their timeline."
        ),
        responses={
            status.HTTP_200_OK: TimelineEntrySerializer(many=True),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Grid never existed"),
        },
        examples=[OpenApiExample("Grid moved", value=MOVE_EXAMPLE, response_only=True)],
    )
    def get(self, request, grid_id: int):
        entries = grid_timeline(grid_id)
        if entries is None:
            return Response({"error": "Grid not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(TimelineEntrySerializer(entries, many=True).data)
