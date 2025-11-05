from cryo_grids.models import CryoGrid, CryoGridBox, Puck, Cane, Specimen
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

from umbrella.choices import CANE_COLORS, GRID_BOX_COLORS, GRID_BOX_NUMBERING, GRID_CASSETTE_NUMBERING, PUCK_COLORS

from .serializers import CryoGridBoxSerializer, GridDetailsSerializer, PuckSerializer, UserSerializer, CaneSerializer, SpecimenSerializer


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
    @action(detail=True, methods=['get'], url_path='slots')
    def slots(self, request, pk=None):
        """
        Get puck slots information showing which positions are filled or empty
        URL: /api/list/pucks/{puck_id}/slots/
        """
        try:
            puck = self.get_object()
            
            # Get all grid boxes for this puck
            grid_boxes = CryoGridBox.objects.filter(puck=puck).values('id', 'position_in_puck')
            
            # Create a mapping of position to grid box
            filled_positions = {box['position_in_puck']: box['id'] for box in grid_boxes}
            
            # Generate slots array for puck positions
            slots = []
            for position in range(1, puck.max_boxes + 1):  # 1 to 12
                if position in filled_positions:
                    slots.append({
                        "position": position,
                        "status": "filled",
                        "grid_box_id": filled_positions[position],
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

    # def retrieve(self, request, *args, **kwargs):
    #     """
    #     Retrieve detailed puck information with related data
    #     """
    #     instance = self.get_object()
    #     # Use select_related and prefetch_related for better performance
    #     instance = Puck.objects.select_related(
    #         'user', 'cane'
    #     ).prefetch_related(
    #         'cryogridbox_set'
    #     ).get(pk=instance.pk)
        
    #     serializer = self.get_serializer(instance)
    #     return Response(serializer.data)

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
                'id', 'name', 'position_in_box',
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

class SpecimenViewSet(viewsets.ReadOnlyModelViewSet):
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