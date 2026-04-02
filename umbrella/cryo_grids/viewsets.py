"""
DRF ViewSets for the cryo_grids app.

Contains ViewSets for managing Pucks, CryoGridBoxes, and grid logging choices.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Case, CharField, Count, F, Prefetch, Q, Value, When
from django.db.models.functions import Lower, StrIndex, Substr, Trim
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
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

from common.auth import CsrfExemptSessionAuthentication
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
    LabelSerializer,
    PuckSerializer,
    SampleSerializer,
    SpecimenSerializer,
)
from cryo_grids.viewset_helpers import (
    add_selected_status,
    apply_grid_box_filters,
    get_shared_search_suggestions,
    msi_session_sort_key,
)


class PuckViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Puck model with full CRUD operations and custom actions
    """

    permission_classes = []  # Allow unauthenticated access
    authentication_classes = []  # Disable authentication
    serializer_class = PuckSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        Filter pucks by user_id or cane_id if provided in query params
        If no user_id, return all pucks
        """
        queryset = Puck.objects.select_related("user", "cane").order_by("name")
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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
    URL: /api/canes/
    """

    permission_classes = []
    authentication_classes = []
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
    URL: /api/specimens/
    """

    permission_classes = []
    authentication_classes = []
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
    URL: /api/samples/
    """

    permission_classes = []
    authentication_classes = []
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
    URL: /api/freezing-sessions/
    """

    permission_classes = []
    authentication_classes = []
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
    authentication_classes = [CsrfExemptSessionAuthentication]

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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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

    @method_decorator(csrf_exempt)
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
            for label_id in label_ids:
                if label_id not in existing_label_ids:
                    GridLabel.objects.create(grid=grid, label_id=label_id, added_by=user)

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
        import json

        from django.utils.timezone import now as tz_now

        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)

        # Parse selected filters
        selected_filters = {}
        for item in q_params:
            category = item.get("category")
            values = item.get("value")
            if category and values:
                selected_filters[category] = set(values if isinstance(values, list) else [values])

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
                .annotate(count=Count("id"))
                .order_by("puck_temp_name")
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
                        When(trashed=True, then=Value("Inactive")),
                        When(trashed=False, then=Value("Active")),
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
    URL: /api/project-leaders/
    """

    permission_classes = []
    authentication_classes = []

    def get_queryset(self):
        """Get only active project_leaders (by project_leader_id in DB)."""
        from projects.models import Project

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
    authentication_classes = [CsrfExemptSessionAuthentication]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)


class CryoGridBoxViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for CryoGridBox model with nested grids.
    URL: /api/list/grid-boxes/
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
    authentication_classes = [CsrfExemptSessionAuthentication]

    def list(self, request, *args, **kwargs):
        """
        List grid boxes with pagination in the format expected by the frontend.
        Returns { result, pagination, sortBy }.
        """
        import json

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
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

        paginator = Paginator(queryset, page_size)
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

    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Return available filter options with counts for grid boxes."""
        import json

        raw_q = request.GET.get("q", "[]")
        q_params = json.loads(raw_q)

        # Parse selected filters
        selected_filters = {}
        for item in q_params:
            category = item.get("category")
            values = item.get("value")
            if category and values:
                selected_filters[category] = set(values if isinstance(values, list) else [values])

        base_qs = CryoGridBox.objects.all()

        def query_filter(qs, filter_expr, value_expr):
            """Query filter options with counts, aliasing as 'filter_name' to avoid conflict with model 'name' field."""
            rows = list(
                qs.filter(**{filter_expr: False})
                .values(filter_name=F(value_expr))
                .annotate(count=Count("id", distinct=True))
                .order_by("filter_name")
            )
            return [{"name": r["filter_name"], "count": r["count"]} for r in rows]

        filters = {
            "project": query_filter(base_qs, "cryogrid__intended_project__isnull", "cryogrid__intended_project__name"),
            "puck": query_filter(base_qs, "puck__isnull", "puck__name"),
            "sample": query_filter(base_qs, "cryogrid__specimen__samples__isnull", "cryogrid__specimen__samples__name"),
            "user": query_filter(base_qs, "cryogrid__user__isnull", "cryogrid__user__username"),
            "cassette": query_filter(base_qs, "cryogrid__grid_cassette__isnull", "cryogrid__grid_cassette__name"),
            "label": query_filter(base_qs, "cryogrid__labels__isnull", "cryogrid__labels__name"),
            "msiSession": query_filter(base_qs, "cryogrid__msisession__isnull", "cryogrid__msisession__name"),
            "screeningSession": query_filter(
                base_qs, "cryogrid__atlassession__group__isnull", "cryogrid__atlassession__group__name"
            ),
            "status": [
                {"name": "Active", "count": base_qs.filter(cryogrid__trashed=False).distinct().count()},
                {"name": "Inactive", "count": base_qs.filter(cryogrid__trashed=True).distinct().count()},
            ],
            "date": [],
        }

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
