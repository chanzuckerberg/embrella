"""
DRF ViewSets for the Umbrella project.

This module contains User-related ViewSets.
For model-specific ViewSets, see respective Django apps:
- cryo_grids.viewsets - PuckViewSet, GridLoggingChoicesViewSet
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.functions import Lower
from rest_framework import viewsets
from rest_framework.response import Response

from .serializers import UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for User model - ReadOnly since we only want to list users
    """

    queryset = User.objects.all().order_by(Lower("username"))
    serializer_class = UserSerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()  # Get count from filtered queryset

            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data["total_users_count"] = total_count
                return response_data

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "total_users_count": total_count,
                    "users": serializer.data,
                }
            )
        except Exception as e:
            return Response(
                {
                    "error": "Internal server error occurred while fetching users",
                    "detail": str(e) if settings.DEBUG else "Please try again later",
                },
                status=500,
            )
