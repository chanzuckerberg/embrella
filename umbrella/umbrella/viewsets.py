from cryo_grids.models import CryoGrid, CryoGridBox, Puck, Cane, Specimen, Sample, PlungeFreezingSession
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.functions import Lower
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from confluence.models import Space, Page
from clouddocs.models import DriveFolder

from umbrella.choices import CANE_COLORS, GRID_BOX_COLORS, GRID_BOX_NUMBERING, GRID_CASSETTE_NUMBERING, PUCK_COLORS

from .serializers import CryoGridBoxSerializer, GridDetailsSerializer, PuckSerializer, UserSerializer, CaneSerializer, SpecimenSerializer, SampleSerializer, FreezingSessionSerializer, CryoGridSerializer, ConfluenceSpaceSerializer, DriveFolderSerializer, ConfluencePageSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for User model - ReadOnly since we only want to list users
    """
    queryset = User.objects.all().order_by(Lower('username'))
    serializer_class = UserSerializer
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()  # Get count from filtered queryset
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_users_count'] = total_count
                return response_data
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_users_count': total_count,
                'users': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching users",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

class PuckViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Puck model - ReadOnly with pagination and user filtering
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
        queryset = Puck.objects.select_related('user', 'cane').order_by('name')
        user_id = self.request.query_params.get('user_id', None)
        cane_id = self.request.query_params.get('cane_id', None)

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
                response_data.data['total_pucks_count'] = total_count
                return response_data
            
            # Fallback (though pagination should always work)
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_pucks_count': total_count,
                'pucks': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching pucks",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @method_decorator(csrf_exempt)
    def create(self, request, *args, **kwargs):
        """
        Create a new puck with validation
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return Response({
                'message': 'Puck created successfully',
                'puck': serializer.data,
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while creating puck",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        """
        pk stands for primary key - puck_id, None means it's optional
        Works on a specific puck, so it needs the pk to identify which puck
        """

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
            from django.db import transaction
            
            puck = self.get_object()
            puck_name = puck.name
            
            stats = {
                'grids_trashed': 0,
                'grid_boxes_deleted': 0,
                'puck_deleted': False
            }
            
            with transaction.atomic():
                # Get all grid boxes belonging to this puck
                grid_boxes = CryoGridBox.objects.filter(puck=puck)
                grid_box_count = grid_boxes.count()
                
                # Get all grids in the grid boxes
                for grid_box in grid_boxes:
                    grids = CryoGrid.objects.filter(
                        grid_box=grid_box,
                        trashed=False
                    )
                    
                    # Trash all grids 
                    grids_updated = grids.update(
                        trashed=True,
                        grid_box=None,
                        position_in_box=None
                    )
                    stats['grids_trashed'] += grids_updated
                
                # Delete all grid boxes
                grid_boxes.delete()
                stats['grid_boxes_deleted'] = grid_box_count
                
                # Delete the puck itself
                puck.delete()
                stats['puck_deleted'] = True
            
            return Response({
                'success': True,
                'message': f'Puck "{puck_name}" deleted successfully',
                'stats': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Failed to delete puck',
                'detail': str(e) if settings.DEBUG else 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='slots')
    def slots(self, request, pk=None):
        """
        Get puck slots information showing which positions are filled or empty
        URL: /api/list/pucks/{puck_id}/slots/
        """
        try:
            puck = self.get_object()
            
            # Get all grid boxes for this puck
            grid_boxes = CryoGridBox.objects.filter(puck=puck).values('id', 'position_in_puck', 'name')
            
            # Create a mapping of position to grid box
            filled_positions = {box['position_in_puck']:{'id': box['id'], 'name': box['name']} for box in grid_boxes}
            
            # Generate slots array for puck positions
            slots = []
            for position in range(1, puck.max_boxes + 1):  # 1 to 12
                if position in filled_positions:
                    slots.append({
                        "position": position,
                        "status": "filled",
                        "grid_box_id": filled_positions[position]['id'],
                        "grid_box_name": filled_positions[position]['name'],
                    })
                else:
                    slots.append({
                        "position": position,
                        "status": "empty",
                    })
            
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
            return Response({
                "error": str(e),
            }, status=500)

    @action(detail=True, methods=['get'], url_path='grid-box/(?P<position_in_puck>[0-9]+)')
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
                return Response({
                    "puck_id": puck.name,
                    "position": int(position_in_puck),
                    "status": "empty",
                })
        
            # Get all grids in this grid box
            grids = CryoGrid.objects.filter(
                grid_box=grid_box,
                trashed=False,
            ).select_related('specimen').values(
                'id', 'name', 'position_in_box', 'clipped',
            )
        
            # Create positions array (1-4 quadrants)
            positions = []
            for q in range(1, grid_box.max_grids + 1):
                grid_at_position = next(
                    (g for g in grids if g['position_in_box'] == q),
                    None,
                )
            
                if grid_at_position:
                    positions.append({
                        "q": q,
                        "occupied": True,
                        "grid_id": f"{grid_at_position['id']}",
                        "grid_name": grid_at_position['name'],
                        "clipped": grid_at_position['clipped'],
                    })
                else:
                    positions.append({
                        "q": q,
                        "occupied": False,
                    })
        
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
            return Response({
            "error": str(e),
            }, status=500)

    @action(detail=True, methods=['get'], url_path='grid-box/(?P<position_in_puck>[0-9]+)/grid/(?P<grid_id>[0-9]+)')
    def grid_details(self, request, pk=None, position_in_puck=None, grid_id=None):
        """
        Get detailed information about a specific grid - matches your Grid Details form exactly
        URL: /api/list/pucks/{puck_id}/grid-box/{position_in_puck}/grid/{grid_id}/
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
                return Response({
                    "error": "Grid box not found at the specified position",
                }, status=404)
            
            # Get the specific grid with all related data
            try:
                grid = CryoGrid.objects.select_related(
                    'user', 'grid_box', 'specimen', 'freezing_session', 'intended_project',
                ).prefetch_related(
                    'specimen__samples',
                ).get(
                    id=grid_id,
                    grid_box=grid_box,
                    trashed=False,
                )
            except CryoGrid.DoesNotExist:
                return Response({
                    "error": "Grid not found",
                }, status=404)
            
            # Use the serializer to get data that matches your UI form exactly
            serializer = GridDetailsSerializer(grid, context={'request': request})
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                "error": "Failed to fetch grid details",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @method_decorator(csrf_exempt)
    @action(detail=True, methods=['post'], url_path='grid-box')
    def create_grid_box(self, request, pk=None):
        """
        Create a new grid box within this puck
        URL: POST /api/list/pucks/{puck_id}/grid-box/
        Response:
        {
            "message": "Grid box created successfully",
            "grid_box": {
                "id": 1,
                "name": "box1",
                "color": "FFFFFF",
                "color_display": "White",
                "numbering": "ucw",
                "numbering_display": "Up Clockwise",
                "position_in_puck": 1,
                "max_grids": 4,
                "puck": 1,
                "puck_user": "user@example.com"
            }
        }
        """
        try:
            puck = self.get_object()

            # Extract puck_name from request if provided (for validation)
            puck_name = request.data.get('puck_name', None)

            if puck_name and puck.name != puck_name:
                return Response({
                    'error': 'Puck name mismatch',
                    'detail': f'Expected puck "{puck.name}" but got "{puck_name}"',
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add puck_id to the request data
            data = request.data.copy()
            data['puck'] = puck.id

            # Remove puck_name from data as it's not a model field
            if 'puck_name' in data:
                del data['puck_name']

            # Create serializer with the data
            serializer = CryoGridBoxSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            grid_box = serializer.save()

            return Response({
                'message': 'Grid box created successfully',
                'grid_box': serializer.data,
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while creating grid box",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['patch'], url_path='grid-box/(?P<grid_box_id>[0-9]+)/update')
    def update_grid_box(self, request, grid_box_id=None):
        """
        Update a grid box's information
        URL: PATCH /api/list/pucks/grid-box/{grid_box_id}/
        
        Request Body:
        {
            "name": "NewBoxName",
            "color": "FF5733",
            "numbering": "ucw"
        }
        
        Response:
        {
            "success": True,
            "message": "Grid box updated successfully",
            "grid_box": {...}
        }
        """
        try:
            from cryo_grids.models import CryoGridBox
            
            # Get the grid box
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Grid box not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the update data from request
            name = request.data.get('name')
            color = request.data.get('color')
            numbering = request.data.get('numbering')
            
            # Update fields if provided
            if name is not None:
                grid_box.name = name
            if color is not None:
                grid_box.color = color
            if numbering is not None:
                grid_box.numbering = numbering
            
            grid_box.save()
            
            # Prepare response
            return Response({
                'success': True,
                'message': 'Grid box updated successfully',
                'grid_box': {
                    'id': grid_box.id,
                    'name': grid_box.name,
                    'color': grid_box.color,
                    'color_display': grid_box.get_color_display(),
                    'numbering': grid_box.numbering,
                    'numbering_display': grid_box.get_numbering_display(),
                    'position_in_puck': grid_box.position_in_puck,
                    'max_grids': grid_box.max_grids,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Failed to update grid box',
                'detail': str(e) if settings.DEBUG else 'An error occurred while updating the grid box',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['delete'], url_path='grid-box/(?P<grid_box_id>[0-9]+)')
    def delete_grid_box(self, request, grid_box_id=None):
        """
        Delete a grid box and handle cascading operations:
        1. Trash all grids in this grid box
        2. Delete the grid box itself
        
        URL: DELETE /api/list/pucks/grid-box/{grid_box_id}/
        
        Response:
        {
            "success": true,
            "message": "Grid box 'box1' deleted successfully",
            "stats": {
                "grids_trashed": 3,
                "grid_box_deleted": true,
                "puck_id": 5,
                "puck_name": "puck1"
            }
        }
        """
        try:
            from django.db import transaction
            
            # Get the grid box to delete
            try:
                grid_box = CryoGridBox.objects.select_related('puck').get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Grid box not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            grid_box_name = grid_box.name
            puck_id = grid_box.puck.id if grid_box.puck else None
            puck_name = grid_box.puck.name if grid_box.puck else None
            
            stats = {
                'grids_trashed': 0,
                'grid_box_deleted': False,
                'puck_id': puck_id,
                'puck_name': puck_name
            }
            
            with transaction.atomic():
                # Get all grids in this grid box that are not already trashed
                grids = CryoGrid.objects.filter(
                    grid_box=grid_box,
                    trashed=False
                )
                
                # Trash all grids and remove them from the grid box
                grids_updated = grids.update(
                    trashed=True,
                    grid_box=None,
                    position_in_box=None
                )
                stats['grids_trashed'] = grids_updated
                
                # Delete the grid box itself
                grid_box.delete()
                stats['grid_box_deleted'] = True
            
            return Response({
                'success': True,
                'message': f'Grid box "{grid_box_name}" deleted successfully',
                'stats': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Failed to delete grid box',
                'detail': str(e) if settings.DEBUG else 'An error occurred while deleting the grid box',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['patch'], url_path='grid-box/(?P<grid_box_id>[0-9]+)/move')
    def move_grid_box(self, request, grid_box_id=None): 
        """
        Move a grid box to a different puck and/or position
        URL: PATCH /api/list/pucks/grid-box/{grid_box_id}/move/
        
        Request Body:
        {
            "destination_puck_id": 5,
            "destination_position": 3
        }
        
        Response:
        {
            "success": True,
            "message": "Grid box moved successfully",
            "grid_box": {
                "id": 1,
                "name": "box1",
                "puck": 5,
                "position_in_puck": 3,
                ...
            }
        }
        """
        try:
            # Get the grid box to move
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Grid box not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Extract destination from request
            destination_puck_id = request.data.get('destination_puck_id')
            destination_position = request.data.get('destination_position')
            
            if not destination_puck_id or not destination_position:
                return Response({
                    'success': False,
                    'error': 'Both destination_puck_id and destination_position are required',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate destination puck exists
            try:
                destination_puck = Puck.objects.get(id=destination_puck_id)
            except Puck.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Destination puck with ID {destination_puck_id} not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate destination position is within puck's range
            if destination_position < 1 or destination_position > destination_puck.max_boxes:
                return Response({
                    'success': False,
                    'error': f'Position must be between 1 and {destination_puck.max_boxes}',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if destination position is already occupied
            existing_box = CryoGridBox.objects.filter(
                puck=destination_puck,
                position_in_puck=destination_position
            ).exclude(id=grid_box_id).first()
            
            if existing_box:
                return Response({
                    'success': False,
                    'error': f'Position {destination_position} in puck {destination_puck.name} is already occupied',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store old location for response message
            old_puck_name = grid_box.puck.name if grid_box.puck else 'None'
            old_position = grid_box.position_in_puck
            
            # Update grid box location
            grid_box.puck = destination_puck
            grid_box.position_in_puck = destination_position
            grid_box.save()
            
            # Serialize updated grid box
            serializer = CryoGridBoxSerializer(grid_box)
            
            return Response({
                'success': True,
                'message': f'Grid box "{grid_box.name}" moved from {old_puck_name} position {old_position} to {destination_puck.name} position {destination_position}',
                'grid_box': serializer.data,
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'success': False,
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Internal server error occurred while moving grid box',
                'detail': str(e) if settings.DEBUG else 'Please try again later',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        return Response({
            "cane_colors": [
                {'value': code, 'label': name}
                for code, name in CANE_COLORS
            ],
            "puck_colors": [
                {'value': code, 'label': name}
                for code, name in PUCK_COLORS
            ],
            "grid_box_colors": [
                {'value': code, 'label': name}
                for code, name in GRID_BOX_COLORS
            ],
            "grid_box_numbering": [
                {'value': code, 'label': name}
                for code, name in GRID_BOX_NUMBERING
            ],
            "grid_cassette_numbering": [
                {'value': code, 'label': name}
                for code, name in GRID_CASSETTE_NUMBERING
            ],
        })
class CaneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Cane model - ReadOnly
    """
    queryset = Cane.objects.all().order_by('id')
    serializer_class = CaneSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'canes': serializer.data,
        })

class SampleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sample model - ReadOnly
    """
    queryset = Sample.objects.all().order_by('name')
    serializer_class = SampleSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        """
        List all samples
        URL: /api/list/samples/
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_samples_count'] = total_count
                return response_data
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_samples_count': total_count,
                'samples': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching samples",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @method_decorator(csrf_exempt) 
    def create(self, request, *args, **kwargs):
        """
        Create a new sample
        URL: POST /api/list/samples/
        """
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                sample = serializer.save()
                return Response({
                    'message': 'Sample created successfully',
                    'sample': SampleSerializer(sample).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Validation failed',
                    'detail': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': 'Failed to create sample',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SpecimenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Specimen model - ReadOnly
    Provides list and retrieve operations for specimens
    """
    queryset = Specimen.objects.prefetch_related('samples').order_by('-id')
    serializer_class = SpecimenSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        """
        List all specimens with their samples
        URL: /api/list/specimens/
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_specimens_count'] = total_count
                return response_data
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_specimens_count': total_count,
                'specimens': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching specimens",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @method_decorator(csrf_exempt) 
    def create(self, request, *args, **kwargs):
        """
        Create a new specimen
        URL: POST /api/list/specimens/
        """
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                specimen = serializer.save()
                return Response({
                    'message': 'Specimen created successfully',
                    'specimen': SpecimenSerializer(specimen).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Validation failed',
                    'detail': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': 'Failed to create specimen',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed information about a specific specimen
        URL: /api/list/specimens/{specimen_id}/
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Specimen.DoesNotExist:
            return Response({
                "error": "Specimen not found",
            }, status=404)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching specimen",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

class FreezingSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PlungeFreezingSession model - ReadOnly
    """
    queryset = PlungeFreezingSession.objects.select_related('user', 'device').order_by('-datetime')
    serializer_class = FreezingSessionSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        """
        List all freezing sessions
        URL: /api/list/freezing-sessions/
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_freezing_sessions_count'] = total_count
                return response_data
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_freezing_sessions_count': total_count,
                'freezing_sessions': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching freezing sessions",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)
    
    @method_decorator(csrf_exempt)
    def create(self, request, *args, **kwargs):
        """
        Create a new freezing session
        URL: POST /api/list/freezing-sessions/
        
        Request Body:
        {
            "user": 1,
            "device": 2,
            "device_temperature": 25.5,
            "humidity": 60.0,
            "notes_page": 123  // optional
        }
        
        Response:
        {
            "message": "Freezing session created successfully",
            "freezing_session": {
                "id": 1,
                "datetime": "2025-11-12T10:30:00Z",
                "user": 1,
                "user_name": "john.doe",
                "device": 2,
                "device_name": "Vitrobot Mark IV",
                "device_temperature": 25.5,
                "humidity": 60.0,
                "notes_page": 123,
                "display_name": "2025-11-12 10:30:00 - john.doe - Vitrobot Mark IV"
            }
        }
        """
        try:
            # Validate required fields
            user_id = request.data.get('user')
            device_id = request.data.get('device')
            
            if not user_id:
                return Response({
                    'error': 'User is required',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not device_id:
                return Response({
                    'error': 'Device is required',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate user exists
            try:
                User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found',
                    'detail': f'No user found with ID {user_id}',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate device exists
            try:
                from cryo_grids.models import PlungeFreezingDevice
                PlungeFreezingDevice.objects.get(id=device_id)
            except PlungeFreezingDevice.DoesNotExist:
                return Response({
                    'error': 'Device not found',
                    'detail': f'No device found with ID {device_id}',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate notes_page if provided
            notes_page_id = request.data.get('notes_page')
            if notes_page_id:
                try:
                    Page.objects.get(id=notes_page_id)
                except Page.DoesNotExist:
                    return Response({
                        'error': 'Notes page not found',
                        'detail': f'No confluence page found with ID {notes_page_id}',
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Create serializer and validate
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return Response({
                'message': 'Freezing session created successfully',
                'freezing_session': serializer.data,
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while creating freezing session",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    @action(detail=False, methods=['get'], url_path='devices')
    def get_devices(self, request):
        """
        Get all unique devices used in freezing sessions
        URL: /api/list/freezing-sessions/devices/
        """
        try:
            from cryo_grids.models import PlungeFreezingDevice
            
            devices = PlungeFreezingDevice.objects.all().order_by('name')
            device_list = [
                {
                    'id': device.id,
                    'name': device.name,
                    'maker_model': device.maker_model
                }
                for device in devices
            ]
            return Response({
                'devices': device_list,
                'total_devices_count': len(device_list),
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching devices",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

class CryoGridViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CryoGrid model
    """
    queryset = CryoGrid.objects.filter(trashed=False).select_related(
        'user', 'grid_box', 'specimen', 'freezing_session', 'intended_project'
    ).order_by('-id')
    serializer_class = CryoGridSerializer
    permission_classes = []
    authentication_classes = []
    
    @method_decorator(csrf_exempt)
    def create(self, request, *args, **kwargs):
        """
        Create a new grid
        URL: POST /api/list/grids/
        
        Request Body:
        {
            "name": "Grid1",
            "user": 1,
            "specimen": 5,
            "intended_project": 3,
            "grid_box": 10,  // grid box ID
            "position_in_box": 1,
            "freezing_session": 2,  // optional
            "notes": "Some notes",  // optional
            "clipped": false,  // optional
            "blot_time": 6.0,  // optional
            "blot_force": 0.0,  // optional
            "blot_distance": 0.0,  // optional
            "copy_number": 1  // optional
        }
        """
        try:
            # Validate grid_box exists
            grid_box_id = request.data.get('grid_box')
            if not grid_box_id:
                return Response({
                    'error': 'grid_box is required',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'error': 'Grid box not found',
                    'detail': f'No grid box found with ID {grid_box_id}',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Prepare data with defaults
            data = request.data.copy()
            if 'copy_number' not in data:
                data['copy_number'] = 1
            if 'clipped' not in data:
                data['clipped'] = False
            if 'trashed' not in data:
                data['trashed'] = False
            
            # Create serializer and validate
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return Response({
                'message': 'Grid created successfully',
                'grid': serializer.data,
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while creating grid",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['patch'], url_path='(?P<grid_id>[0-9]+)/move')
    def move_grid(self, request, grid_id=None):
        """
        Move a grid to a different grid box and/or position
        URL: PATCH /api/list/grids/{grid_id}/move/
        
        Request Body:
        {
            "destination_grid_box_id": 10,
            "destination_position": 2
        }
        
        Response:
        {
            "success": true,
            "message": "Grid moved successfully",
            "grid": {
                "id": 5,
                "name": "Grid1",
                "grid_box": 10,
                "position_in_box": 2,
                ...
            }
        }
        """
        try:
            # Get the grid to move
            try:
                grid = CryoGrid.objects.get(id=grid_id, trashed=False)
            except CryoGrid.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Grid not found or has been trashed',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Extract destination from request
            destination_grid_box_id = request.data.get('destination_grid_box_id')
            destination_position = request.data.get('destination_position')
            
            if not destination_grid_box_id or not destination_position:
                return Response({
                    'success': False,
                    'error': 'Both destination_grid_box_id and destination_position are required',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate destination grid box exists
            try:
                destination_grid_box = CryoGridBox.objects.get(id=destination_grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Destination grid box with ID {destination_grid_box_id} not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate destination position is within grid box's range
            if destination_position < 1 or destination_position > destination_grid_box.max_grids:
                return Response({
                    'success': False,
                    'error': f'Position must be between 1 and {destination_grid_box.max_grids}',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if destination position is already occupied by another grid
            existing_grid = CryoGrid.objects.filter(
                grid_box=destination_grid_box,
                position_in_box=destination_position,
                trashed=False
            ).exclude(id=grid_id).first()
            
            if existing_grid:
                return Response({
                    'success': False,
                    'error': f'Position {destination_position} in grid box {destination_grid_box.name} is already occupied by grid "{existing_grid.name}"',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store old location for response message
            old_grid_box_name = grid.grid_box.name if grid.grid_box else 'None'
            old_position = grid.position_in_box
            
            # Update grid location
            grid.grid_box = destination_grid_box
            grid.position_in_box = destination_position
            grid.save()
            
            # Serialize updated grid
            serializer = CryoGridSerializer(grid)
            
            return Response({
                'success': True,
                'message': f'Grid "{grid.name}" moved from {old_grid_box_name} position {old_position} to {destination_grid_box.name} position {destination_position}',
                'grid': serializer.data,
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'success': False,
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Internal server error occurred while moving grid',
                'detail': str(e) if settings.DEBUG else 'Please try again later',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['post'], url_path='clip-all-in-box/(?P<grid_box_id>[0-9]+)')
    @method_decorator(csrf_exempt)
    def clip_all_in_box(self, request, grid_box_id=None):
        """
        Clip all grids in a specific grid box
        URL: POST /api/list/grids/clip-all-in-box/<grid_box_id>/
        
        Example: POST /api/list/grids/clip-all-in-box/42/
        """
        try:
            # Get the grid box
            try:
                grid_box = CryoGridBox.objects.get(id=grid_box_id)
            except CryoGridBox.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Grid box not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get all non-trashed grids in this box
            grids = CryoGrid.objects.filter(
                grid_box=grid_box,
                trashed=False,
                clipped=False
            )
            
            # Count how many grids will be affected
            grids_count = grids.count()
            
            if grids_count == 0:
                return Response({
                    'success': False,
                    'error': 'No grids found in this grid box',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update all grids to clipped=True
            updated_count = grids.update(clipped=True)
            
            return Response({
                'success': True,
                'message': f'Successfully clipped {updated_count} grid(s)',
                'updated_count': updated_count,
                'grid_box_id': int(grid_box_id),
                'grid_box_name': grid_box.name,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e) if settings.DEBUG else 'Internal server error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConfluenceSpaceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Confluence Spaces"""
    queryset = Space.objects.all().order_by('name')
    serializer_class = ConfluenceSpaceSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'spaces': serializer.data,
                'total_count': queryset.count(),
            })
        except Exception as e:
            return Response({
                "error": "Failed to fetch confluence spaces",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

class ConfluencePageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Confluence Pages (for notes pages in specimens/freezing sessions)"""
    queryset = Page.objects.all().order_by('name')
    serializer_class = ConfluencePageSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'pages': serializer.data,
                'total_count': queryset.count(),
            })
        except Exception as e:
            return Response({
                "error": "Failed to fetch confluence pages",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)
    
class DriveFolderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Google Drive Folders"""
    queryset = DriveFolder.objects.all().order_by('name')
    serializer_class = DriveFolderSerializer
    permission_classes = []
    authentication_classes = []
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'folders': serializer.data,
                'total_count': queryset.count(),
            })
        except Exception as e:
            return Response({
                "error": "Failed to fetch drive folders",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

class ProjectLeaderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Project Leaders - Returns only staff users who can be project leaders
    """
    queryset = User.objects.filter(is_staff=True).order_by(Lower('username'))
    serializer_class = UserSerializer
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_count'] = total_count
                return response_data
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_count': total_count,
                'users': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching project leaders",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)