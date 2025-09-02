from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from cryo_grids.models import Puck
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
        """
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()
        
        # Always use pagination for better performance
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