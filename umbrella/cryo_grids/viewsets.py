"""
DRF ViewSets for the cryo_grids app.

Contains ViewSets for managing Pucks, CryoGridBoxes, and grid logging choices.
"""

import json
from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models, transaction
from django.db.models import (
    Case,
    CharField,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Lower, StrIndex, Substr, Trim
from django.utils.timezone import now as tz_now
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer
from projects.models import Project
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from umbrella.choices import (
    CANE_COLORS,
    GRID_BOX_COLORS,
    GRID_BOX_NUMBERING,
    GRID_CASSETTE_NUMBERING,
    PUCK_COLORS,
)

from cryo_grids.models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    GridLabel,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Sample,
    Specimen,
)
from cryo_grids.serializers import (
    CaneSerializer,
    CryoGridBoxListSerializer,
    CryoGridBoxSerializer,
    CryoGridSerializer,
    FreezingSessionSerializer,
    GridDetailsSerializer,
    GridInBoxSerializer,
    LabelSerializer,
    PuckSerializer,
    SampleSerializer,
    SpecimenSerializer,
)
from cryo_grids.viewset_helpers import (
    add_selected_status,
    apply_grid_box_filters,
    apply_shared_grid_inventory_filters,
    get_shared_filterlist_options,
    get_shared_search_suggestions,
    msi_session_sort_key,
    natural_name_annotations,
    natural_name_ordering,
    parse_selected_filters,
)


class PuckViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Puck model with full CRUD operations and custom actions
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = PuckSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        Filter pucks by user_id or cane_id if provided in query params
        If no user_id, return all pucks
        """
        queryset = (
            Puck.objects.select_related("user", "cane")
            .annotate(**natural_name_annotations())
            .order_by(*natural_name_ordering())
        )
        user_id = self.request.query_params.get("user_id", None)
        cane_id = self.request.query_params.get("cane_id", None)

        if user_id is not None:
            try:
                user_id = int(user_id)
                # Check if user exists
                if not User.objects.filter(id=user_id).exists():
                    raise ValidationError(f"User with ID {user_id} does not exist")
                queryset = queryset.filter(user_id=user_id)
            except ValueError:
                raise ValidationError("Invalid user_id format. Must be a number.")

        if cane_id is not None:
            try:
                cane_id = int(cane_id)
                queryset = queryset.filter(cane_id=cane_id)
            except ValueError:
                raise ValidationError("Invalid cane_id format. Must be a number.")

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Handle pagination and return appropriate response
        Handles collections of objects, so it doesn't need a specific ID
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()

            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                # Add total count to paginated response
                response_data.data["total_pucks_count"] = total_count
                return response_data

            # Fallback (though pagination should always work)
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "total_pucks_count": total_count,
                    "pucks": serializer.data,
                }
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while fetching pucks",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=500,
            )

    def create(self, request, *args, **kwargs):
        """
        Create a new puck with validation
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return Response(
                {
                    "message": "Puck created successfully",
                    "puck": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while creating puck",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="slots")
    def slots(self, request, pk=None):
        """
        Get puck slots information showing which positions are filled or empty
        URL: /api/list/pucks/{puck_id}/slots/
        """
        try:
            puck = self.get_object()

            # Get all grid boxes for this puck
            grid_boxes = CryoGridBox.objects.filter(puck=puck).values("id", "position_in_puck", "name")

            # Create a mapping of position to grid box info
            filled_positions = {box["position_in_puck"]: {"id": box["id"], "name": box["name"]} for box in grid_boxes}

            # Generate slots array for puck positions
            slots = []
            for position in range(1, puck.max_boxes + 1):  # 1 to 12
                if position in filled_positions:
                    slots.append(
                        {
                            "position": position,
                            "status": "filled",
                            "grid_box_id": filled_positions[position]["id"],
                            "grid_box_name": filled_positions[position]["name"],
                        }
                    )
                else:
                    slots.append(
                        {
                            "position": position,
                            "status": "empty",
                        }
                    )

            # Calculate summary
            filled_count = len(filled_positions)
            empty_count = puck.max_boxes - filled_count

            response_data = {
                "puck_id": str(puck.id),
                "puck_name": puck.name,
                "slots": slots,
                "slot_summary": {
                    "total": puck.max_boxes,
                    "filled_count": filled_count,
                    "empty_count": empty_count,
                },
            }

            return Response(response_data)

        except Exception as e:
            return Response(
                {
                    "error": str(e),
                },
                status=500,
            )

    @action(detail=True, methods=["get"], url_path="grid-box/(?P<position_in_puck>[0-9]+)")
    def grid_box_detail(self, request, pk=None, position_in_puck=None):
        """
        Get detailed grid box information for a specific position in a puck
        URL: /api/list/pucks/{puck_id}/grid-box/{position_in_puck}/
        """
        try:
            puck = self.get_object()

            # Get the grid box at the specified position
            try:
                grid_box = CryoGridBox.objects.get(
                    puck=puck,
                    position_in_puck=position_in_puck,
                )
            except CryoGridBox.DoesNotExist:
                # Return empty slot response
                return Response(
                    {
                        "puck_id": puck.name,
                        "position": int(position_in_puck),
                        "status": "empty",
                    }
                )

            # Get all grids in this grid box
            grids = (
                CryoGrid.objects.filter(
                    grid_box=grid_box,
                    trashed=False,
                )
                .select_related("specimen")
                .values(
                    "id",
                    "name",
                    "position_in_box",
                    "clipped",
                )
            )

            # Create positions array (1-4 quadrants)
            positions = []
            for q in range(1, grid_box.max_grids + 1):
                grid_at_position = next(
                    (g for g in grids if g["position_in_box"] == q),
                    None,
                )

                if grid_at_position:
                    positions.append(
                        {
                            "q": q,
                            "occupied": True,
                            "grid_id": f"{grid_at_position['id']}",
                            "grid_name": grid_at_position["name"],
                            "clipped": grid_at_position["clipped"],
                        }
                    )
                else:
                    positions.append(
                        {
                            "q": q,
                            "occupied": False,
                        }
                    )

            response_data = {
                "puck_id": puck.id,
                "puck_name": puck.name,
                "position_in_puck": int(position_in_puck),
                "status": "filled",
                "max_grids": grid_box.max_grids,
                "grid_box": {
                    "grid_box_id": grid_box.id,
                    "name": grid_box.name,
                    "color": grid_box.color,
                    "color_display": grid_box.get_color_display(),
                    "numbering": grid_box.numbering,
                    "numbering_display": grid_box.get_numbering_display(),
                    "max_grids": grid_box.max_grids,
                    "positions": positions,
                },
            }

            return Response(response_data)

        except Exception as e:
            return Response(
                {
                    "error": str(e),
                },
                status=500,
            )

    @action(detail=True, methods=["post"], url_path="grid-box")
    def create_grid_box(self, request, pk=None):
        """
        Create a new grid box within this puck
        URL: POST /api/list/pucks/{puck_id}/grid-box/
        """
        try:
            puck = self.get_object()

            # Extract puck_name from request if provided (for validation)
            puck_name = request.data.get("puck_name", None)

            if puck_name and puck.name != puck_name:
                return Response(
                    {
                        "error": "Puck name mismatch",
                        "detail": f'Expected puck "{puck.name}" but got "{puck_name}"',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add puck_id to the request data
            data = request.data.copy()
            data["puck"] = puck.id

            # Remove puck_name from data as it's not a model field
            if "puck_name" in data:
                del data["puck_name"]

            # Create serializer with the data
            serializer = CryoGridBoxSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            grid_box = serializer.save()

            return Response(
                {
                    "message": "Grid box created successfully",
                    "grid_box": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while creating grid box",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a puck and handle cascading operations:
        1. Trash all grids in grid boxes belonging to this puck
        2. Delete all grid boxes in this puck
        3. Delete the puck itself

        URL: DELETE /api/list/pucks/{puck_id}/
        """
        try:
            puck = self.get_object()
            puck_name = puck.name

            stats = {
                "grids_trashed": 0,
                "grid_boxes_deleted": 0,
                "puck_deleted": False,
            }

            with transaction.atomic():
                # Get all grid boxes belonging to this puck
                grid_boxes = CryoGridBox.objects.filter(puck=puck)
                grid_box_count = grid_boxes.count()

                # Get all grids in the grid boxes
                for grid_box in grid_boxes:
                    grids = CryoGrid.objects.filter(
                        grid_box=grid_box,
                        trashed=False,
                    )

                    # Trash all grids
                    grids_updated = grids.update(
                        trashed=True,
                        grid_box=None,
                        position_in_box=None,
                    )
                    stats["grids_trashed"] += grids_updated

                # Delete all grid boxes
                grid_boxes.delete()
                stats["grid_boxes_deleted"] = grid_box_count

                # Delete the puck itself
                puck.delete()
                stats["puck_deleted"] = True

            return Response(
                {
                    "success": True,
                    "message": f'Puck "{puck_name}" deleted successfully',
                    "stats": stats,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Failed to delete puck",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path="grid-box/(?P<grid_box_id>[0-9]+)/update")
    def update_grid_box(self, request, grid_box_id=None):
        """
        Update a grid box's information
        URL: PATCH /api/list/pucks/grid-box/{grid_box_id}/update/
        """
        try:
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid box not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Use serializer for validation and update
            serializer = CryoGridBoxSerializer(grid_box, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Grid box updated successfully",
                    "grid_box": {
                        "id": grid_box.id,
                        "name": grid_box.name,
                        "color": grid_box.color,
                        "color_display": grid_box.get_color_display(),
                        "numbering": grid_box.numbering,
                        "numbering_display": grid_box.get_numbering_display(),
                        "position_in_puck": grid_box.position_in_puck,
                        "max_grids": grid_box.max_grids,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Failed to update grid box",
                    "detail": str(e) if settings.DEBUG else "An error occurred while updating the grid box",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["delete"], url_path="grid-box/(?P<grid_box_id>[0-9]+)")
    def delete_grid_box(self, request, grid_box_id=None):
        """
        Delete a grid box and trash all grids inside it
        URL: DELETE /api/list/pucks/grid-box/{grid_box_id}/
        """
        try:
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid box not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            grid_box_name = grid_box.name
            stats = {"grids_trashed": 0}

            with transaction.atomic():
                # Trash all grids in the grid box
                grids = CryoGrid.objects.filter(grid_box=grid_box, trashed=False)
                stats["grids_trashed"] = grids.update(
                    trashed=True,
                    grid_box=None,
                    position_in_box=None,
                )

                # Delete the grid box
                grid_box.delete()

            return Response(
                {
                    "success": True,
                    "message": f'Grid box "{grid_box_name}" deleted successfully',
                    "stats": stats,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Failed to delete grid box",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path="grid-box/(?P<grid_box_id>[0-9]+)/move")
    def move_grid_box(self, request, grid_box_id=None):
        """
        Move a grid box to a different puck and/or position
        URL: PATCH /api/list/pucks/grid-box/{grid_box_id}/move/
        """
        try:
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid box not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_puck_id = request.data.get("puck_id")
            new_position = request.data.get("position_in_puck")

            if not new_puck_id or not new_position:
                return Response(
                    {
                        "success": False,
                        "error": "Both puck_id and position_in_puck are required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                new_puck = Puck.objects.get(id=new_puck_id)
            except Puck.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": f"Puck with ID {new_puck_id} not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_position = int(new_position)

            # Check if position is valid for the puck
            if new_position < 1 or new_position > new_puck.max_boxes:
                return Response(
                    {
                        "success": False,
                        "error": f"Position must be between 1 and {new_puck.max_boxes}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if position is already occupied (excluding current grid box)
            existing = (
                CryoGridBox.objects.filter(
                    puck=new_puck,
                    position_in_puck=new_position,
                )
                .exclude(id=grid_box_id)
                .first()
            )

            if existing:
                return Response(
                    {
                        "success": False,
                        "error": f'Position {new_position} in puck is already occupied by "{existing.name}"',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the grid box
            old_puck_name = grid_box.puck.name if grid_box.puck else "None"
            old_position = grid_box.position_in_puck

            grid_box.puck = new_puck
            grid_box.position_in_puck = new_position
            grid_box.save()

            return Response(
                {
                    "success": True,
                    "message": "Grid box moved successfully",
                    "grid_box": {
                        "id": grid_box.id,
                        "name": grid_box.name,
                        "old_puck": old_puck_name,
                        "old_position": old_position,
                        "new_puck": new_puck.name,
                        "new_position": new_position,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Failed to move grid box",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GridLoggingChoicesViewSet(viewsets.ViewSet):
    """
    ViewSet for grid logging choices (colors, numbering patterns...)
    READ-ONLY - returns static configuration choices
    """

    def list(self, request):
        """
        Get all choices for grid logging forms
        URL: /api/grid-logging/choices/
        """
        return Response(
            {
                "cane_colors": [{"value": code, "label": name} for code, name in CANE_COLORS],
                "puck_colors": [{"value": code, "label": name} for code, name in PUCK_COLORS],
                "grid_box_colors": [{"value": code, "label": name} for code, name in GRID_BOX_COLORS],
                "grid_box_numbering": [{"value": code, "label": name} for code, name in GRID_BOX_NUMBERING],
                "grid_cassette_numbering": [{"value": code, "label": name} for code, name in GRID_CASSETTE_NUMBERING],
            }
        )


class CaneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing Canes
    READ-ONLY - supports list and retrieve
    URL: /api/list/canes/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = CaneSerializer
    queryset = Cane.objects.select_related("dewar").order_by("name")

    def list(self, request, *args, **kwargs):
        """
        List all canes with pagination support
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Optional filtering by dewar_id
        dewar_id = request.query_params.get("dewar_id")
        if dewar_id:
            queryset = queryset.filter(dewar_id=dewar_id)

        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "canes": serializer.data,
                "total_count": queryset.count(),
            }
        )


class SpecimenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Specimen model with full CRUD operations
    URL: /api/list/specimens/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = SpecimenSerializer
    queryset = Specimen.objects.prefetch_related("samples").select_related("documentation_page")

    def list(self, request, *args, **kwargs):
        """List all specimens"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "specimens": serializer.data,
                "total_count": queryset.count(),
            }
        )

    def create(self, request, *args, **kwargs):
        """Create a new specimen"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            specimen = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Specimen created successfully",
                    "specimen": SpecimenSerializer(specimen).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed information about a specific specimen.
        URL: GET /api/list/specimens/{specimen_id}/
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Specimen.DoesNotExist:
            return Response(
                {
                    "error": "Specimen not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while fetching specimen",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SampleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sample model with full CRUD operations
    URL: /api/list/samples/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = SampleSerializer
    queryset = Sample.objects.all().order_by(Lower("name"))

    def list(self, request, *args, **kwargs):
        """List all samples"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "samples": serializer.data,
                "total_count": queryset.count(),
            }
        )

    def create(self, request, *args, **kwargs):
        """Create a new sample"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            sample = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Sample created successfully",
                    "sample": SampleSerializer(sample).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FreezingSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PlungeFreezingSession model with full CRUD operations
    URL: /api/list/freezing-sessions/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = FreezingSessionSerializer
    queryset = PlungeFreezingSession.objects.select_related(
        "user",
        "device",
        "documentation_page",
    ).order_by("-datetime")

    def list(self, request, *args, **kwargs):
        """List all freezing sessions"""
        queryset = self.filter_queryset(self.get_queryset())

        # Optional filtering by user_id
        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "freezing_sessions": serializer.data,
                "total_count": queryset.count(),
            }
        )

    def create(self, request, *args, **kwargs):
        """Create a new freezing session"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            session = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Freezing session created successfully",
                    "freezing_session": FreezingSessionSerializer(session).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="devices")
    def get_devices(self, request):
        """
        Get all plunge freezing devices.
        URL: /api/list/freezing-sessions/devices/
        """
        try:
            devices = PlungeFreezingDevice.objects.all().order_by("name")
            device_list = [
                {
                    "id": device.id,
                    "name": device.name,
                    "maker_model": device.maker_model,
                }
                for device in devices
            ]
            return Response(
                {
                    "devices": device_list,
                    "total_devices_count": len(device_list),
                }
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while fetching devices",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CryoGridViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CryoGrid model
    URL: /cryo_grids/v1/grids/
    """

    queryset = (
        CryoGrid.objects.filter(trashed=False)
        .select_related(
            "user",
            "grid_box",
            "specimen",
            "freezing_session",
            "intended_project",
        )
        .order_by("-id")
    )
    serializer_class = CryoGridSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def list(self, request, *args, **kwargs):
        """Delegate to the existing grid list view for backwards compatibility."""
        from cryo_grids.views import get_cryo_grids_details

        return get_cryo_grids_details(request)

    def retrieve(self, request, *args, **kwargs):
        """Return full grid details using GridDetailsSerializer."""
        try:
            grid = (
                CryoGrid.objects.select_related(
                    "user",
                    "grid_box",
                    "grid_box__puck",
                    "specimen",
                    "freezing_session",
                    "freezing_session__user",
                    "freezing_session__device",
                    "intended_project",
                )
                .prefetch_related("specimen__samples")
                .get(id=kwargs.get("pk"))
            )
        except CryoGrid.DoesNotExist:
            return Response({"error": "Grid not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = GridDetailsSerializer(grid, context={"request": request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create a new grid"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            grid = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Grid created successfully",
                    "grid": CryoGridSerializer(grid).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<grid_id>[0-9]+)/duplicate")
    def duplicate(self, request, grid_id=None):
        """
        Duplicate a grid into a destination box ``number_to_copy`` times.
        URL: POST /cryo_grids/v1/grids/{grid_id}/duplicate/

        Body: {"destination_grid_box_id": int, "number_to_copy": int}
        """
        from cryo_grids.services import DuplicateGridError, duplicate_grid

        try:
            source_grid = CryoGrid.objects.get(id=grid_id)
        except CryoGrid.DoesNotExist:
            return Response(
                {"success": False, "error": "Grid not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        destination_grid_box_id = request.data.get("destination_grid_box_id")
        number_to_copy = request.data.get("number_to_copy")

        if destination_grid_box_id is None or number_to_copy is None:
            return Response(
                {
                    "success": False,
                    "error": "Both destination_grid_box_id and number_to_copy are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            number_to_copy = int(number_to_copy)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "number_to_copy must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            destination_box = CryoGridBox.objects.get(id=destination_grid_box_id)
        except CryoGridBox.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": f"Destination grid box with ID {destination_grid_box_id} not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            new_grids = duplicate_grid(
                source_grid=source_grid,
                destination_box=destination_box,
                number_to_copy=number_to_copy,
                request_user=request.user if request.user.is_authenticated else None,
            )
        except DuplicateGridError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = (
            f'Duplicated grid "{source_grid.name}" into {destination_box.name} '
            f"({len(new_grids)} {'copies' if len(new_grids) != 1 else 'copy'})"
        )
        return Response(
            {
                "success": True,
                "message": message,
                "new_grid_ids": [g.id for g in new_grids],
                "grids": CryoGridSerializer(new_grids, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["patch"], url_path=r"(?P<grid_id>[0-9]+)/move")
    def move_grid(self, request, grid_id=None):
        """
        Move a grid to a different grid box and/or position.
        URL: PATCH /api/list/grids/{grid_id}/move/
        """
        try:
            try:
                grid = CryoGrid.objects.get(id=grid_id, trashed=False)
            except CryoGrid.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid not found or has been trashed",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            destination_grid_box_id = request.data.get("destination_grid_box_id")
            destination_position = request.data.get("destination_position")

            if not destination_grid_box_id or not destination_position:
                return Response(
                    {
                        "success": False,
                        "error": "Both destination_grid_box_id and destination_position are required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                destination_grid_box = CryoGridBox.objects.get(id=destination_grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": f"Destination grid box with ID {destination_grid_box_id} not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            destination_position = int(destination_position)

            # Validate position is within grid box's range
            if destination_position < 1 or destination_position > destination_grid_box.max_grids:
                return Response(
                    {
                        "success": False,
                        "error": f"Position must be between 1 and {destination_grid_box.max_grids}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if destination position is already occupied
            existing_grid = (
                CryoGrid.objects.filter(
                    grid_box=destination_grid_box,
                    position_in_box=destination_position,
                    trashed=False,
                )
                .exclude(id=grid_id)
                .first()
            )

            if existing_grid:
                return Response(
                    {
                        "success": False,
                        "error": f'Position {destination_position} in grid box {destination_grid_box.name} is already occupied by grid "{existing_grid.name}"',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Store old location for response
            old_grid_box_name = grid.grid_box.name if grid.grid_box else "None"
            old_position = grid.position_in_box

            # Update grid location
            grid.grid_box = destination_grid_box
            grid.position_in_box = destination_position
            grid.save()

            return Response(
                {
                    "success": True,
                    "message": f'Grid "{grid.name}" moved from {old_grid_box_name} position {old_position} to {destination_grid_box.name} position {destination_position}',
                    "grid": CryoGridSerializer(grid).data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Internal server error occurred while moving grid",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path=r"(?P<grid_id>[0-9]+)/update")
    def update_grid(self, request, grid_id=None):
        """
        Update a grid's information.
        URL: PATCH /api/list/grids/{grid_id}/update/
        """
        try:
            try:
                grid = CryoGrid.objects.get(id=grid_id, trashed=False)
            except CryoGrid.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid not found or has been trashed",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = CryoGridSerializer(grid, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Grid updated successfully",
                    "grid": CryoGridSerializer(grid).data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation error",
                    "detail": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Failed to update grid",
                    "detail": str(e) if settings.DEBUG else "An error occurred while updating the grid",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"clip-all-in-box/(?P<grid_box_id>[0-9]+)")
    def clip_all_in_box(self, request, grid_box_id=None):
        """
        Clip all grids in a specific grid box.
        URL: POST /api/list/grids/clip-all-in-box/{grid_box_id}/
        """
        try:
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid box not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get all non-trashed, unclipped grids in this box
            grids = CryoGrid.objects.filter(
                grid_box=grid_box,
                trashed=False,
                clipped=False,
            )

            grids_count = grids.count()

            if grids_count == 0:
                return Response(
                    {
                        "success": True,
                        "message": "No unclipped grids found in this grid box",
                        "updated_count": 0,
                    },
                    status=status.HTTP_200_OK,
                )

            # Update all grids to clipped=True
            updated_count = grids.update(clipped=True)

            return Response(
                {
                    "success": True,
                    "message": f"Successfully clipped {updated_count} grid(s)",
                    "updated_count": updated_count,
                    "grid_box_id": int(grid_box_id),
                    "grid_box_name": grid_box.name,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e) if settings.DEBUG else "Internal server error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["patch"], url_path=r"(?P<grid_id>[0-9]+)/update-labels")
    def update_labels(self, request, grid_id=None):
        """
        Set labels on a grid. Accepts {"label_ids": [1,2,3]}.
        URL: PATCH /api/list/grids/{grid_id}/update-labels/
        """
        try:
            try:
                grid = CryoGrid.objects.get(id=grid_id)
            except CryoGrid.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "error": "Grid not found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            label_ids = request.data.get("label_ids", [])
            if not isinstance(label_ids, list):
                return Response(
                    {
                        "success": False,
                        "error": "label_ids must be a list of integers",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            labels = Label.objects.filter(id__in=label_ids)
            if labels.count() != len(label_ids):
                return Response(
                    {
                        "success": False,
                        "error": "One or more label IDs are invalid",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = request.user if request.user.is_authenticated else None

            # Remove labels not in the new set
            removed_links = GridLabel.objects.filter(grid=grid).exclude(label_id__in=label_ids)
            removed_label_ids = set(removed_links.values_list("label_id", flat=True))
            removed_links.delete()

            # Auto-delete recently created labels (< 1 min old) that are now unused.
            # This catches typos from label creation without removing established labels.
            if removed_label_ids:
                import datetime

                from django.utils import timezone

                one_minute_ago = timezone.now() - datetime.timedelta(minutes=1)
                Label.objects.filter(
                    id__in=removed_label_ids,
                    created_at__gte=one_minute_ago,
                ).exclude(id__in=GridLabel.objects.values_list("label_id", flat=True)).delete()

            # Add new labels
            existing_label_ids = set(GridLabel.objects.filter(grid=grid).values_list("label_id", flat=True))
            added = False
            for label_id in label_ids:
                if label_id not in existing_label_ids:
                    GridLabel.objects.create(grid=grid, label_id=label_id, added_by=user)
                    added = True

            # Bump the grid's updated_on (auto_now only fires on save())
            if added or removed_label_ids:
                grid.save(update_fields=["updated_on"])

            return Response(
                {
                    "success": True,
                    "message": "Labels updated successfully",
                    "labels": LabelSerializer(grid.labels.order_by("gridlabel__added_at"), many=True).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e) if settings.DEBUG else "Internal server error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Return available filter options with counts for grids."""
        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)

        selected_filters = parse_selected_filters(q_params)

        queryset = CryoGrid.objects.select_related(
            "intended_project",
            "freezing_session",
            "grid_box__puck",
            "user",
            "grid_cassette",
            "specimen",
            "sample",
        ).prefetch_related(
            "msisession",
            "specimen__samples",
            "atlassession__group",
            "labels",
        )

        current_time = tz_now()
        date_ranges = {
            "last_1_month": current_time - timedelta(days=30),
            "last_3_months": current_time - timedelta(days=90),
            "last_6_months": current_time - timedelta(days=180),
        }

        filters = {
            "project": list(
                queryset.annotate(project_temp_name=F("intended_project__name"))
                .values(project_temp_name=F("project_temp_name"))
                .annotate(count=Count("id"))
                .order_by("project_temp_name")
                .values(name=F("project_temp_name"), count=F("count"))
            ),
            "puck": list(
                queryset.annotate(puck_temp_name=F("grid_box__puck__name"))
                .filter(puck_temp_name__isnull=False)
                .values(puck_temp_name=F("puck_temp_name"))
                .annotate(count=Count("id"), **natural_name_annotations("grid_box__puck__name"))
                .order_by(*natural_name_ordering("puck_temp_name"))
                .values(name=F("puck_temp_name"), count=F("count"))
            ),
            "sample": list(
                queryset.annotate(sample_temp_name=F("specimen__samples__name"))
                .filter(sample_temp_name__isnull=False)
                .values(sample_temp_name=F("sample_temp_name"))
                .annotate(count=Count("id"))
                .order_by("sample_temp_name")
                .values(name=F("sample_temp_name"), count=F("count"))
            ),
            "label": list(
                queryset.annotate(label_temp_name=F("labels__name"))
                .filter(label_temp_name__isnull=False)
                .values(label_temp_name=F("label_temp_name"))
                .annotate(count=Count("id"))
                .order_by("label_temp_name")
                .values(name=F("label_temp_name"), count=F("count"))
            ),
            "cassette": list(
                queryset.annotate(cassette_temp_name=F("grid_cassette__name"))
                .filter(cassette_temp_name__isnull=False)
                .values(cassette_temp_name=F("cassette_temp_name"))
                .annotate(count=Count("id"))
                .order_by("cassette_temp_name")
                .values(name=F("cassette_temp_name"), count=F("count"))
            ),
            "screeningSession": list(
                queryset.filter(freezing_session__isnull=False)
                .annotate(screen_session_temp_name=F("atlassession__group__name"))
                .filter(screen_session_temp_name__isnull=False)
                .values(screen_session_temp_name=F("screen_session_temp_name"))
                .annotate(count=Count("id"))
                .order_by("screen_session_temp_name")
                .values(name=F("screen_session_temp_name"), count=F("count"))
            ),
            "user": list(
                queryset.annotate(
                    user_temp_name=Trim(
                        Case(
                            When(
                                user__username__contains="@",
                                then=Substr(F("user__username"), 1, StrIndex(F("user__username"), Value("@")) - 1),
                            ),
                            default=F("user__username"),
                            output_field=CharField(),
                        ),
                    ),
                )
                .values(user_temp_name=F("user_temp_name"))
                .annotate(count=Count("id"))
                .order_by("user_temp_name")
                .values(name=Trim(F("user_temp_name")), count=F("count"))
            ),
            "msiSession": sorted(
                list(
                    queryset.filter(msisession__isnull=False)
                    .annotate(msi_session_temp_name=F("msisession__name"))
                    .values(msi_session_temp_name=F("msi_session_temp_name"))
                    .annotate(count=Count("id"))
                    .values(name=F("msi_session_temp_name"), count=F("count")),
                ),
                key=lambda x: msi_session_sort_key(x["name"]),
            ),
            "status": list(
                queryset.annotate(
                    status_name=Case(
                        When(trashed=True, then=Value("Trashed")),
                        When(trashed=False, then=Value("Not Trashed")),
                        output_field=CharField(),
                    )
                )
                .values("status_name")
                .annotate(count=Count("id"))
                .order_by("status_name")
                .values(name=F("status_name"), count=F("count"))
            ),
            "date": [
                {"name": "last_1_month", "count": queryset.filter(create_on__gte=date_ranges["last_1_month"]).count()},
                {
                    "name": "last_3_months",
                    "count": queryset.filter(create_on__gte=date_ranges["last_3_months"]).count(),
                },
                {
                    "name": "last_6_months",
                    "count": queryset.filter(create_on__gte=date_ranges["last_6_months"]).count(),
                },
            ],
        }

        # Enrich sample names with ontology
        processed_samples = []
        for item in filters["sample"]:
            if "name" in item and item["name"]:
                try:
                    sample_obj = Sample.objects.get(name=item["name"])
                    display_name = sample_obj.name
                    if sample_obj.ontology:
                        display_name += f" ({sample_obj.ontology})"
                    processed_samples.append(
                        {
                            "name": display_name,
                            "count": item["count"],
                            "selected": False,
                        }
                    )
                except Sample.DoesNotExist:
                    processed_samples.append(item)
            else:
                processed_samples.append(item)
        filters["sample"] = processed_samples

        for key, filter_list in filters.items():
            add_selected_status(filter_list, key, selected_filters)

        return Response({"filters": filters})

    @action(detail=False, methods=["get"], url_path="search_suggestions")
    def search_suggestions(self, request):
        """Return search suggestions for grids."""
        term = request.GET.get("term", "").strip()
        if len(term) < 1:
            return Response({"suggestions": []})

        limit = 5
        suggestions = []

        # Grid names (entity-specific)
        for name in CryoGrid.objects.filter(name__icontains=term).values_list("name", flat=True).distinct()[:limit]:
            suggestions.append({"value": name, "category": "grid"})

        suggestions.extend(get_shared_search_suggestions(term, limit))
        return Response({"suggestions": suggestions[:20]})


class ProjectLeaderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing users who can be project leaders
    READ-ONLY - supports list and retrieve
    URL: /api/list/project-leaders/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def get_queryset(self):
        """Get only active project_leaders (by project_leader_id in DB)."""
        leader_ids = (
            Project.objects.filter(project_leader_id__isnull=False)
            .values_list("project_leader_id", flat=True)
            .distinct()
        )
        return User.objects.filter(id__in=leader_ids, is_active=True).order_by("username")

    def list(self, request, *args, **kwargs):
        """List all potential project leaders"""
        queryset = self.get_queryset()

        leaders = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
            }
            for user in queryset
        ]

        return Response(
            {
                "project_leaders": leaders,
                "total_count": len(leaders),
            }
        )


class LabelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Label model - full CRUD.
    URL: /api/list/labels/
    """

    queryset = Label.objects.annotate(usage_count=models.Count("grids")).order_by("-usage_count", "name")
    serializer_class = LabelSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)


class CryoGridBoxViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for CryoGridBox model with nested grids.
    URL: /api/cryo_grids/v1/grid-boxes/
    """

    queryset = (
        CryoGridBox.objects.select_related("puck", "puck__user")
        .prefetch_related(
            Prefetch(
                "cryogrid_set",
                queryset=CryoGrid.objects.filter(trashed=False)
                .select_related("specimen", "user", "intended_project")
                .prefetch_related("labels", "specimen__samples"),
            ),
        )
        .annotate(grid_count=Count("cryogrid", filter=Q(cryogrid__trashed=False), distinct=True))
        .order_by("-id")
    )
    serializer_class = CryoGridBoxListSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def list(self, request, *args, **kwargs):
        """
        List grid boxes with pagination in the format expected by the frontend.
        Returns { result, pagination, sortBy }.
        """
        queryset = self.filter_queryset(self.get_queryset())

        raw_q = request.GET.get("q", None)
        q_params = json.loads(raw_q) if raw_q else []

        # Apply filters
        queryset = apply_grid_box_filters(queryset, q_params)

        page = 1
        page_size = 10
        sort_field = "id"
        asc = False

        for item in q_params:
            category = item.get("category")
            value = item.get("value")
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            if category == "page":
                page = int(value)
            elif category == "pageSize":
                page_size = int(value)
            elif category == "sort":
                sort_field = value
            elif category == "asc":
                asc = bool(value) if isinstance(value, bool) else str(value).lower() == "true"

        # Map camelCase frontend field names to Django model/annotation names
        sort_field_map = {
            "gridCount": "grid_count",
        }
        db_sort_field = sort_field_map.get(sort_field, sort_field)
        sort_order = db_sort_field if asc else f"-{db_sort_field}"
        queryset = queryset.order_by(sort_order)

        # Paginate
        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = self.get_serializer(page_obj.object_list, many=True)

        # Transform to camelCase with gridBox primary entity
        result = []
        for item in serializer.data:
            result.append(
                {
                    "gridBox": {
                        "id": item["id"],
                        "name": item["name"],
                    },
                    "color": item["color"],
                    "colorDisplay": item["color_display"],
                    "numberingDisplay": item["numbering_display"],
                    "puckName": item["puck_name"],
                    "positionInPuck": item["position_in_puck"],
                    "maxGrids": item["max_grids"],
                    "gridCount": item["grid_count"],
                    "puckUser": item["puck_user"],
                    "grids": item["grids"],
                },
            )

        return Response(
            {
                "result": result,
                "pagination": {
                    "page": page_obj.number,
                    "pageSize": page_size,
                    "totalPages": paginator.num_pages,
                    "totalResults": paginator.count,
                },
                "sortBy": {
                    "sort": sort_field,
                    "asc": asc,
                },
            },
        )

    @action(detail=False, methods=["get"], url_path="available_positions")
    def available_positions(self, request):
        """
        Return position availability for a grid box.
        URL: GET /cryo_grids/v1/grid-boxes/available_positions/?box_id={id}
        """
        from cryo_grids.services import get_available_positions

        box_id = request.GET.get("box_id")
        if not box_id:
            return Response(
                {"success": False, "error": "box_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            box = CryoGridBox.objects.get(pk=box_id)
        except (CryoGridBox.DoesNotExist, ValueError):
            return Response(
                {"success": False, "error": "Grid box not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        available = get_available_positions(box)
        max_grids = box.max_grids or 4
        used = sorted(set(range(1, max_grids + 1)) - set(available))
        return Response(
            {
                "box_id": box.id,
                "max_grids": max_grids,
                "used_positions": used,
                "available_positions": available,
                "available_count": len(available),
            }
        )

    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Return available filter options with counts for grid boxes."""
        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)

        selected_filters = parse_selected_filters(q_params)
        base_qs = CryoGridBox.objects.all()

        filters = get_shared_filterlist_options(base_qs, grid_prefix="cryogrid__")

        # Add grid-box-specific filter: puck (direct relation, not via grid), natural sort
        puck_rows = list(
            base_qs.filter(puck__isnull=False)
            .values(filter_name=F("puck__name"))
            .annotate(count=Count("id", distinct=True), **natural_name_annotations("puck__name"))
            .order_by(*natural_name_ordering("filter_name"))
        )
        filters["puck"] = [{"name": r["filter_name"], "count": r["count"]} for r in puck_rows]
        filters["date"] = []

        for key, filter_list in filters.items():
            if key != "date":
                add_selected_status(filter_list, key, selected_filters)

        return Response({"filters": filters})

    @action(detail=False, methods=["get"], url_path="search_suggestions")
    def search_suggestions(self, request):
        """Return search suggestions for grid boxes."""
        term = request.GET.get("term", "").strip()
        if len(term) < 1:
            return Response({"suggestions": []})

        limit = 5
        suggestions = []

        # Grid box names (entity-specific)
        for name in CryoGridBox.objects.filter(name__icontains=term).values_list("name", flat=True).distinct()[:limit]:
            suggestions.append({"value": name, "category": "gridBox"})

        suggestions.extend(get_shared_search_suggestions(term, limit))
        return Response({"suggestions": suggestions[:20]})


class PuckListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Puck list view with nested grid boxes and grids.
    URL: /cryo_grids/v1/pucks/
    """

    queryset = (
        Puck.objects.select_related("cane", "user")
        .prefetch_related(
            Prefetch(
                "cryogridbox_set",
                queryset=CryoGridBox.objects.prefetch_related(
                    Prefetch(
                        "cryogrid_set",
                        queryset=CryoGrid.objects.filter(trashed=False)
                        .select_related("specimen", "user", "intended_project")
                        .prefetch_related("labels", "specimen__samples"),
                    ),
                )
                .annotate(grid_count=Count("cryogrid", filter=Q(cryogrid__trashed=False), distinct=True))
                .order_by("position_in_puck"),
            ),
        )
        .annotate(grid_box_count=Count("cryogridbox", distinct=True), **natural_name_annotations())
        .order_by(*natural_name_ordering())
    )
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def list(self, request, *args, **kwargs):
        """List pucks with pagination in the format expected by the frontend."""
        from cryo_grids.serializers import PuckListSerializer

        queryset = self.filter_queryset(self.get_queryset())

        raw_q = request.GET.get("q", None)
        q_params = json.loads(raw_q) if raw_q else []

        # Apply shared grid-inventory filters (via grid box → grid)
        queryset = apply_shared_grid_inventory_filters(queryset, q_params, grid_prefix="cryogridbox__cryogrid__")

        # Apply puck-specific filters
        for item in q_params:
            category = item.get("category")
            values = item.get("value")

            if category == "puck" and values:
                if values is None or (isinstance(values, list) and None in values):
                    queryset = queryset.filter(name__isnull=True)
                else:
                    puck_values = values if isinstance(values, list) else [values]
                    queryset = queryset.filter(name__in=puck_values)
            elif category == "search" and values:
                search_terms = values if isinstance(values, list) else [values]
                search_q = Q()
                for t in search_terms:
                    if t:
                        term_q = Q(name__icontains=t)
                        if t.isdigit():
                            term_q |= Q(cryogridbox__cryogrid__id=int(t))
                        search_q |= term_q
                if search_q:
                    queryset = queryset.filter(search_q).distinct()

        # Parse pagination/sort params
        page = 1
        page_size = 10
        sort_field = "id"
        asc = False

        for item in q_params:
            category = item.get("category")
            value = item.get("value")
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            if category == "page":
                page = int(value)
            elif category == "pageSize":
                page_size = int(value)
            elif category == "sort":
                sort_field = value
            elif category == "asc":
                asc = bool(value) if isinstance(value, bool) else str(value).lower() == "true"

        sort_field_map = {
            "gridBoxCount": "grid_box_count",
            "caneName": "cane__name",
        }
        db_sort_field = sort_field_map.get(sort_field, sort_field)

        # Natural sort for name: numbers first (ascending), then words
        if db_sort_field == "name":
            queryset = queryset.order_by(*natural_name_ordering(desc=not asc))
        elif db_sort_field == "id" and not asc:
            # Default sort: use natural name ordering instead of -id
            queryset = queryset.order_by(*natural_name_ordering())
        else:
            sort_order = db_sort_field if asc else f"-{db_sort_field}"
            queryset = queryset.order_by(sort_order)

        # Paginate
        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = PuckListSerializer(page_obj.object_list, many=True)

        # Transform to camelCase with puck primary entity
        result = []
        for item in serializer.data:
            grid_boxes = []
            for gb in item["grid_boxes"]:
                grid_boxes.append(
                    {
                        "gridBox": {
                            "id": gb["id"],
                            "name": gb["name"],
                        },
                        "color": gb["color"],
                        "colorDisplay": gb["color_display"],
                        "numberingDisplay": gb["numbering_display"],
                        "positionInPuck": gb["position_in_puck"],
                        "maxGrids": gb["max_grids"],
                        "gridCount": gb["grid_count"],
                        "grids": gb["grids"],
                    },
                )
            result.append(
                {
                    "puck": {
                        "id": item["id"],
                        "name": item["name"],
                    },
                    "color": item["color"],
                    "colorDisplay": item["color_display"],
                    "caneName": item["cane_name"],
                    "positionInCane": item["position_in_cane"],
                    "maxBoxes": item["max_boxes"],
                    "gridBoxCount": item["grid_box_count"],
                    "userName": item["user_name"],
                    "gridBoxes": grid_boxes,
                },
            )

        return Response(
            {
                "result": result,
                "pagination": {
                    "page": page_obj.number,
                    "pageSize": page_size,
                    "totalPages": paginator.num_pages,
                    "totalResults": paginator.count,
                },
                "sortBy": {
                    "sort": sort_field,
                    "asc": asc,
                },
            },
        )

    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Return available filter options with counts for pucks."""
        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)

        selected_filters = parse_selected_filters(q_params)
        base_qs = Puck.objects.all()

        filters = get_shared_filterlist_options(base_qs, grid_prefix="cryogridbox__cryogrid__")

        # Puck-specific filter: puck name (direct field), natural sort (numbers first)
        puck_rows = list(
            base_qs.values(filter_name=F("name"))
            .annotate(count=Count("id", distinct=True), **natural_name_annotations())
            .order_by(*natural_name_ordering("filter_name"))
        )
        filters["puck"] = [{"name": r["filter_name"], "count": r["count"]} for r in puck_rows]
        filters["date"] = []

        for key, filter_list in filters.items():
            if key != "date":
                add_selected_status(filter_list, key, selected_filters)

        return Response({"filters": filters})

    @action(detail=False, methods=["get"], url_path="search_suggestions")
    def search_suggestions(self, request):
        """Return search suggestions for pucks."""
        term = request.GET.get("term", "").strip()
        if len(term) < 1:
            return Response({"suggestions": []})

        limit = 5
        suggestions = []

        # Puck names (entity-specific)
        for name in Puck.objects.filter(name__icontains=term).values_list("name", flat=True).distinct()[:limit]:
            suggestions.append({"value": name, "category": "puck"})

        suggestions.extend(get_shared_search_suggestions(term, limit))
        return Response({"suggestions": suggestions[:20]})


class GridInventoryCountsViewSet(viewsets.ViewSet):
    """
    Returns filtered counts for all GridInventory tabs in a single request.
    URL: /cryo_grids/v1/counts/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def list(self, request):
        raw_q = request.GET.get("q", None)
        q_params = json.loads(raw_q) if raw_q else []

        # Shared grid-relation filters applied to each entity
        grids_qs = apply_shared_grid_inventory_filters(CryoGrid.objects.filter(trashed=False), q_params, grid_prefix="")
        grid_boxes_qs = apply_shared_grid_inventory_filters(
            CryoGridBox.objects.all(), q_params, grid_prefix="cryogrid__"
        )
        pucks_qs = apply_shared_grid_inventory_filters(
            Puck.objects.all(), q_params, grid_prefix="cryogridbox__cryogrid__"
        )

        # Entity-specific filters (puck, search) for accurate counts
        for item in q_params:
            category = item.get("category")
            values = item.get("value")

            if category == "puck" and values:
                if values is None or (isinstance(values, list) and None in values):
                    grids_qs = grids_qs.filter(grid_box__puck__isnull=True)
                    grid_boxes_qs = grid_boxes_qs.filter(puck__isnull=True)
                    pucks_qs = pucks_qs.filter(name__isnull=True)
                else:
                    puck_values = values if isinstance(values, list) else [values]
                    grids_qs = grids_qs.filter(grid_box__puck__name__in=puck_values)
                    grid_boxes_qs = grid_boxes_qs.filter(puck__name__in=puck_values)
                    pucks_qs = pucks_qs.filter(name__in=puck_values)
            elif category == "search" and values:
                search_terms = values if isinstance(values, list) else [values]
                # Grids search
                grid_search_q = Q()
                for t in search_terms:
                    if t:
                        t_q = (
                            Q(name__icontains=t)
                            | Q(intended_project__name__icontains=t)
                            | Q(user__username__icontains=t)
                            | Q(specimen__samples__name__icontains=t)
                            | Q(labels__name__icontains=t)
                        )
                        if t.isdigit():
                            t_q |= Q(id=int(t))
                        grid_search_q |= t_q
                if grid_search_q:
                    grids_qs = grids_qs.filter(grid_search_q)
                # Grid boxes search
                gb_search_q = Q()
                for t in search_terms:
                    if t:
                        t_q = (
                            Q(name__icontains=t)
                            | Q(cryogrid__name__icontains=t)
                            | Q(cryogrid__intended_project__name__icontains=t)
                            | Q(cryogrid__user__username__icontains=t)
                            | Q(cryogrid__specimen__samples__name__icontains=t)
                            | Q(cryogrid__labels__name__icontains=t)
                        )
                        if t.isdigit():
                            t_q |= Q(cryogrid__id=int(t))
                        gb_search_q |= t_q
                if gb_search_q:
                    grid_boxes_qs = grid_boxes_qs.filter(gb_search_q)
                # Pucks search
                puck_search_q = Q()
                for t in search_terms:
                    if t:
                        t_q = Q(name__icontains=t)
                        if t.isdigit():
                            t_q |= Q(cryogridbox__cryogrid__id=int(t))
                        puck_search_q |= t_q
                if puck_search_q:
                    pucks_qs = pucks_qs.filter(puck_search_q)

        return Response(
            {
                "grids": grids_qs.distinct().count(),
                "gridBoxes": grid_boxes_qs.distinct().count(),
                "pucks": pucks_qs.distinct().count(),
            }
        )


class StandardSamplesViewSet(viewsets.ViewSet):
    """
    Read-only ViewSet that aggregates specimens with grids labeled "standard".
    Returns specimens with available (non-trashed) grid counts and point of contact.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def list(self, request, *args, **kwargs):
        raw_q = request.GET.get("q", None)
        q_params = json.loads(raw_q) if raw_q else []

        page = 1
        page_size = 10
        sort_field = "availableGridCount"
        asc = False

        for item in q_params:
            category = item.get("category")
            value = item.get("value")
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            if category == "page":
                page = int(value)
            elif category == "pageSize":
                page_size = int(value)
            elif category == "sort":
                sort_field = value
            elif category == "asc":
                asc = bool(value) if isinstance(value, bool) else str(value).lower() == "true"

        sort_field_map = {
            "availableGridCount": "available_grid_count",
            "specimen": "specimen_name",
        }
        db_sort_field = sort_field_map.get(sort_field, sort_field)
        sort_order = db_sort_field if asc else f"-{db_sort_field}"

        queryset = (
            Specimen.objects.filter(
                cryogrid__trashed=False,
                cryogrid__labels__name__iexact="standard",
            )
            .prefetch_related(
                Prefetch(
                    "cryogrid_set",
                    queryset=CryoGrid.objects.filter(
                        trashed=False,
                        labels__name__iexact="standard",
                    )
                    .select_related("specimen", "user", "intended_project")
                    .prefetch_related("labels", "specimen__samples")
                    .order_by("id"),
                    to_attr="standard_grids",
                ),
                "samples",
            )
            .annotate(
                available_grid_count=Count(
                    "cryogrid",
                    filter=Q(cryogrid__trashed=False, cryogrid__labels__name__iexact="standard"),
                    distinct=True,
                ),
                specimen_name=models.Value("", output_field=CharField()),
            )
            .distinct()
            .order_by(sort_order)
        )

        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        result = []
        for specimen in page_obj.object_list:
            grids = specimen.standard_grids
            grid_data = GridInBoxSerializer(grids, many=True).data

            # Derive point of contact as most common grid user
            users = [g.user.username for g in grids if g.user]
            point_of_contact = Counter(users).most_common(1)[0][0] if users else None

            specimen_name = str(specimen)

            result.append(
                {
                    "specimen": {
                        "id": specimen.id,
                        "name": specimen_name,
                    },
                    "availableGridCount": len(grids),
                    "pointOfContact": point_of_contact,
                    "grids": grid_data,
                }
            )

        return Response(
            {
                "result": result,
                "pagination": {
                    "page": page_obj.number,
                    "pageSize": page_size,
                    "totalPages": paginator.num_pages,
                    "totalResults": paginator.count,
                },
                "sortBy": {
                    "sort": sort_field,
                    "asc": asc,
                },
            },
        )


_ScreeningLinkSerializer = inline_serializer(
    name="ScreeningFreezingSessionLink",
    fields={
        "id": drf_serializers.IntegerField(),
        "name": drf_serializers.CharField(),
        "url": drf_serializers.URLField(),
    },
)

_ScreeningLabelSerializer = inline_serializer(
    name="ScreeningLabel",
    fields={
        "id": drf_serializers.IntegerField(),
        "name": drf_serializers.CharField(),
        "color": drf_serializers.CharField(),
    },
)

_ScreeningGridRowSerializer = inline_serializer(
    name="ScreeningGridRow",
    fields={
        "grid": inline_serializer(
            name="ScreeningGridRef",
            fields={
                "id": drf_serializers.IntegerField(),
                "name": drf_serializers.CharField(),
                "updatedAt": drf_serializers.CharField(allow_null=True),
            },
        ),
        "project": _ScreeningLinkSerializer,
        "specimen_name": drf_serializers.CharField(allow_null=True),
        "user_name": drf_serializers.CharField(allow_null=True),
        "clipped": drf_serializers.BooleanField(),
        "freezing_session": _ScreeningLinkSerializer,
        "labels": _ScreeningLabelSerializer.__class__(many=True),
    },
)

_ScreeningResponseSerializer = inline_serializer(
    name="ScreeningGridsResponse",
    fields={
        "result": _ScreeningGridRowSerializer.__class__(many=True),
        "pagination": inline_serializer(
            name="ScreeningPagination",
            fields={
                "page": drf_serializers.IntegerField(),
                "pageSize": drf_serializers.IntegerField(),
                "totalPages": drf_serializers.IntegerField(),
                "totalResults": drf_serializers.IntegerField(),
            },
        ),
        "sortBy": inline_serializer(
            name="ScreeningSortBy",
            fields={
                "sort": drf_serializers.CharField(),
                "asc": drf_serializers.BooleanField(),
            },
        ),
    },
)


class ScreeningGridsViewSet(viewsets.ViewSet):
    """
    Read-only ViewSet that returns grids tagged with a screening status label.
    Matches both the short form (`TBS`, `TBC`, `TBM`) and the long form
    (`To Be Screened`, `To Be Collected`, `To Be Milled`). Used to power the
    Screening tab.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    STATUS_LABELS = [
        "TBS",
        "TBC",
        "TBM",
        "To Be Screened",
        "To Be Collected",
        "To Be Milled",
    ]

    # Filter groups map a display name
    STATUS_FILTER_GROUPS = {
        "To Be Screened": ["TBS", "To Be Screened"],
        "To Be Collected": ["TBC", "To Be Collected"],
        "To Be Milled": ["TBM", "To Be Milled"],
    }
    MICROSCOPE_FILTER_GROUPS = {
        "Arctis": ["Arctis"],
        "Hydra 1": ["Hydra1"],
        "Hydra 2": ["Hydra2"],
        "Krios 1": ["Krios1"],
        "Krios 2": ["Krios2"],
    }
    PRIORITY_FILTER_GROUPS = {
        "P1": ["P1"],
        "P2": ["P2"],
        "P3": ["P3"],
    }

    # Filter category -> the label group map it draws its options from.
    LABEL_FILTER_GROUPS = {
        "screeningStatus": STATUS_FILTER_GROUPS,
        "microscope": MICROSCOPE_FILTER_GROUPS,
        "priority": PRIORITY_FILTER_GROUPS,
    }

    @classmethod
    def _base_screening_queryset(cls):
        """Non-trashed grids that carry at least one screening status label."""
        return CryoGrid.objects.filter(trashed=False).filter(
            Exists(
                GridLabel.objects.filter(
                    grid=OuterRef("pk"),
                    label__name__in=cls.STATUS_LABELS,
                )
            )
        )

    @classmethod
    def _apply_screening_filters(cls, queryset, q_params):
        """Narrow a screening queryset by the sidebar filter categories.

        Label-based categories (screeningStatus/microscope/priority) reverse-map the
        selected display names to label names
        """
        for item in q_params:
            category = item.get("category")
            values = item.get("value")
            if category in ("page", "pageSize", "sort", "asc") or not values:
                continue
            if not isinstance(values, list):
                values = [values]

            if category in cls.LABEL_FILTER_GROUPS:
                groups = cls.LABEL_FILTER_GROUPS[category]
                label_names = [name for value in values for name in groups.get(value, [value])]
                queryset = queryset.filter(
                    Exists(
                        GridLabel.objects.filter(
                            grid=OuterRef("pk"),
                            label__name__in=label_names,
                        )
                    )
                )
            elif category == "project":
                queryset = queryset.filter(intended_project__name__in=values)

        return queryset

    @extend_schema(
        summary="List grids in the screening pipeline",
        description=(
            "Returns non-trashed grids that have at least one screening status label. "
            "Both short (`TBS`/`TBC`/`TBM`) and long (`To Be Screened`/`To Be Collected`/"
            "`To Be Milled`) forms are accepted. The Priority column sort uses the "
            "lowest-numbered `P1`/`P2`/`P3` label attached to each grid; grids without "
            "a priority label sort last in ascending order. Pagination, sort field, and "
            "direction are passed via the `q` query parameter as a JSON-encoded list of "
            "`{category, value}` entries."
        ),
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "JSON-encoded array of `{category, value}` entries. Sort/pagination categories: "
                    "`page` (int), `pageSize` (int), `sort` (one of `priority`, `status`, "
                    "`microscope`, `name`, `project`, `updatedAt`), `asc` (bool). Filter categories "
                    "(values are lists): `screeningStatus`, `microscope`, `priority` (display names "
                    "from the corresponding label groups) and `project` (intended project name). "
                    "Filter categories combine with AND."
                ),
                examples=[
                    OpenApiExample(
                        "Sort by priority ascending, page 1",
                        value='[{"category":"sort","value":"priority"},'
                        '{"category":"asc","value":true},'
                        '{"category":"page","value":1}]',
                    ),
                    OpenApiExample(
                        "Filter by microscope (Arctis or Krios 1)",
                        value='[{"category":"microscope","value":["Arctis","Krios 1"]}]',
                    ),
                ],
            ),
        ],
        responses={200: _ScreeningResponseSerializer},
    )
    def list(self, request, *args, **kwargs):
        raw_q = request.GET.get("q", None)
        q_params = json.loads(raw_q) if raw_q else []

        page = 1
        page_size = 12
        sort_field = "priority"
        asc = True

        for item in q_params:
            category = item.get("category")
            value = item.get("value")
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            if category == "page":
                page = int(value)
            elif category == "pageSize":
                page_size = int(value)
            elif category == "sort":
                sort_field = value
            elif category == "asc":
                asc = bool(value) if isinstance(value, bool) else str(value).lower() == "true"

        sort_field_map = {
            "priority": "priority_rank",
            "status": "status_rank",
            "microscope": "microscope_rank",
            "name": "name",
            "project": "intended_project__name",
            "updatedAt": "updated_on",
        }
        db_sort_field = sort_field_map.get(sort_field, "priority_rank")
        sort_order = db_sort_field if asc else f"-{db_sort_field}"

        queryset = (
            self._apply_screening_filters(self._base_screening_queryset(), q_params)
            .select_related("intended_project", "specimen", "user", "freezing_session__user")
            .prefetch_related("labels", "specimen__samples")
            .annotate(
                priority_rank=Coalesce(
                    models.Min(
                        Case(
                            When(labels__name__in=["P1", "P2", "P3"], then=F("labels__name")),
                            output_field=CharField(),
                        )
                    ),
                    Value("ZZZ"),
                ),
                # Rank by screening status in workflow order (screened -> collected -> milled)
                status_rank=Coalesce(
                    models.Min(
                        Case(
                            When(labels__name__in=["TBS", "To Be Screened"], then=Value(1)),
                            When(labels__name__in=["TBC", "To Be Collected"], then=Value(2)),
                            When(labels__name__in=["TBM", "To Be Milled"], then=Value(3)),
                            output_field=IntegerField(),
                        )
                    ),
                    Value(99),
                ),
                # Rank by microscope label name (Arctis < Hydra1 < Hydra2 < Krios1 < Krios2
                microscope_rank=Coalesce(
                    models.Min(
                        Case(
                            When(
                                labels__name__in=["Arctis", "Hydra1", "Hydra2", "Krios1", "Krios2"],
                                then=F("labels__name"),
                            ),
                            output_field=CharField(),
                        )
                    ),
                    Value("ZZZ"),
                ),
            )
            .order_by(sort_order, "id")
        )

        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        from cryo_grids.views import format_freezing_session_link, format_project_link

        result = []
        for grid in page_obj.object_list:
            freezing_session = format_freezing_session_link(grid.freezing_session)
            project = format_project_link(grid.intended_project)

            labels = [{"id": label.id, "name": label.name, "color": label.color} for label in grid.labels.all()]

            result.append(
                {
                    "grid": {
                        "id": grid.id,
                        "name": grid.name,
                        "updatedAt": grid.updated_on.isoformat() if grid.updated_on else None,
                    },
                    "project": project,
                    "specimen_name": str(grid.specimen) if grid.specimen else None,
                    "user_name": grid.user.username if grid.user else None,
                    "clipped": grid.clipped,
                    "freezing_session": freezing_session,
                    "labels": labels,
                }
            )

        return Response(
            {
                "result": result,
                "pagination": {
                    "page": page_obj.number,
                    "pageSize": page_size,
                    "totalPages": paginator.num_pages,
                    "totalResults": paginator.count,
                },
                "sortBy": {
                    "sort": sort_field,
                    "asc": asc,
                },
            },
        )

    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Return available screening filter options with counts.

        Powers the screening sidebar: Status, Microscope, Priority (label-based) and
        Project. Label options use display names matching the table chips; counts are
        over non-trashed grids that carry a screening status label.
        """
        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)
        selected_filters = parse_selected_filters(q_params)

        base_qs = self._base_screening_queryset()

        def group_count(label_names):
            return base_qs.filter(
                Exists(
                    GridLabel.objects.filter(
                        grid=OuterRef("pk"),
                        label__name__in=label_names,
                    )
                )
            ).count()

        filters = {}
        for category, groups in self.LABEL_FILTER_GROUPS.items():
            options = []
            for display_name, label_names in groups.items():
                count = group_count(label_names)
                if count > 0:
                    options.append({"name": display_name, "count": count})
            filters[category] = options

        filters["project"] = [
            {"name": row["project_name"], "count": row["count"]}
            for row in (
                base_qs.filter(intended_project__isnull=False)
                .values(project_name=F("intended_project__name"))
                .annotate(count=Count("id", distinct=True))
                .order_by("project_name")
            )
        ]

        for key, filter_list in filters.items():
            add_selected_status(filter_list, key, selected_filters)

        return Response({"filters": filters})
