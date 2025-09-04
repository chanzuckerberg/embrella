from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from rest_framework.decorators import action
from cryo_grids.models import Puck, CryoGridBox, CryoGrid
from .serializers import UserSerializer, PuckSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for User model - ReadOnly since we only want to list users
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    
    def list(self, request, *args, **kwargs):
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
            'users': serializer.data
        })


class PuckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Puck model - ReadOnly with pagination and user filtering
    """
    serializer_class = PuckSerializer
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        """
        Filter pucks by user_id if provided in query params
        If no user_id, return all pucks
        """
        queryset = Puck.objects.select_related('user', 'cane').order_by('name')
        user_id = self.request.query_params.get('user_id', None)
        
        if user_id is not None:
            # Filter by specific user
            queryset = queryset.filter(user_id=user_id)
        
        # Always return ordered queryset (all pucks or filtered by user)
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Handle pagination and return appropriate response
        Handles collections of objects, so it doesn't need a specific ID
        """
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
            'pucks': serializer.data
        })

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
                        "grid_box_id": filled_positions[position]
                    })
                else:
                    slots.append({
                        "position": position,
                        "status": "empty"
                    })
            
            # Calculate summary
            filled_count = len(filled_positions)
            empty_count = puck.max_boxes - filled_count
            
            response_data = {
                "id": str(puck.id),
                "puck_name": puck.name,
                "slots": slots,
                "slot_summary": {
                    "total": puck.max_boxes,
                    "filled_count": filled_count,
                    "empty_count": empty_count
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response({
                "error": str(e)
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
                    position_in_puck=position_in_puck
                )
            except CryoGridBox.DoesNotExist:
                # Return empty slot response
                return Response({
                    "puck_id": puck.name,
                    "position": int(position_in_puck),
                    "status": "empty"
                })
        
            # Get all grids in this grid box
            grids = CryoGrid.objects.filter(
                grid_box=grid_box,
                trashed=False
            ).select_related('specimen').values(
                'id', 'name', 'position_in_box'
            )
        
            # Create positions array (1-4 quadrants)
            positions = []
            for q in range(1, grid_box.max_grids + 1):
                grid_at_position = next(
                    (g for g in grids if g['position_in_box'] == q), 
                    None
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
                        "occupied": False
                    })
        
            response_data = {
                "puck_id": puck.id,
                "puck_name": puck.name,
                "position_in_puck": int(position_in_puck),
                "status": "filled",
                "max_grids": grid_box.max_grids,
                "grid_box": {
                    "id": grid_box.id,
                    "name": grid_box.name,
                    "color": grid_box.color,
                    "color_display": grid_box.get_color_display(),
                    "numbering": grid_box.numbering,
                    "numbering_display": grid_box.get_numbering_display(),
                    "max_grids": grid_box.max_grids,
                    "positions": positions
                }
            }
        
            return Response(response_data)
        
        except Exception as e:
            return Response({
            "error": str(e)
            }, status=500)
   