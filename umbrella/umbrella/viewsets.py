from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from rest_framework.decorators import action
from cryo_grids.models import Puck, CryoGridBox
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
            
            # Generate slots array for positions 1-12
            slots = []
            for position in range(1, 13):  # 1 to 12
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
            empty_count = 12 - filled_count
            
            response_data = {
                "id": str(puck.id),
                "puck_name": puck.name,
                "slots": slots,
                "slotSummary": {
                    "total": 12,
                    "filledCount": filled_count,
                    "emptyCount": empty_count
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