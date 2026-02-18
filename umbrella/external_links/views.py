from django.conf import settings
from rest_framework import status, viewsets
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from workflow.views.job_api import CsrfExemptSessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from external_links.models import ExternalResource
from external_links.serializers import ExternalResourceListSerializer, ExternalResourceSerializer

@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
class ExternalResourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ExternalResource model - handles documentation spaces and pages
    """
    serializer_class = ExternalResourceSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        Filter resources by resource_type or system_name if provided in query params
        """
        queryset = ExternalResource.objects.all().order_by('system_name', 'name')
        resource_type = self.request.query_params.get('resource_type', None)
        system_name = self.request.query_params.get('system_name', None)

        if resource_type:
            valid_types = [choice[0] for choice in ExternalResource.RESOURCE_TYPE_CHOICES]
            if resource_type not in valid_types:
                raise ValidationError(
                    f"Invalid resource_type. Must be one of: {', '.join(valid_types)}"
                )
            queryset = queryset.filter(resource_type=resource_type)

        if system_name:
            queryset = queryset.filter(system_name__iexact=system_name)

        return queryset

    def get_serializer_class(self):
        """
        Use lightweight serializer for list view
        """
        if self.action == 'list':
            return ExternalResourceListSerializer
        return ExternalResourceSerializer

    def list(self, request, *args, **kwargs):
        """
        List external resources with optional filtering
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            total_count = queryset.count()

            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
                response_data.data['total_resources_count'] = total_count
                return response_data

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'total_resources_count': total_count,
                'resources': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching resources",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    def create(self, request, *args, **kwargs):
        """
        Create a new external resource
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return Response({
                'message': 'External resource created successfully',
                'resource': serializer.data,
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while creating resource",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """
        Update an external resource
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response({
                'message': 'External resource updated successfully',
                'resource': serializer.data,
            })
        except ValidationError as e:
            return Response({
                'error': 'Validation error',
                'detail': e.detail,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while updating resource",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an external resource
        """
        try:
            instance = self.get_object()
            instance_name = instance.name
            self.perform_destroy(instance)

            return Response({
                'message': f'External resource "{instance_name}" deleted successfully',
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while deleting resource",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def doc_spaces(self, request):
        """
        Get all documentation spaces (Confluence spaces, Google Drive folders, etc.)
        URL: /api/external-resources/doc_spaces/
        """
        try:
            resources = ExternalResource.objects.filter(
                resource_type='doc_space'
            ).order_by('system_name', 'name')

            system_name = request.query_params.get('system_name', None)
            if system_name:
                resources = resources.filter(system_name__iexact=system_name)

            serializer = ExternalResourceListSerializer(resources, many=True)
            return Response({
                'count': resources.count(),
                'doc_spaces': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching doc spaces",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @action(detail=False, methods=['get'])
    def doc_pages(self, request):
        """
        Get all documentation pages (Confluence pages, Benchling entries, etc.)
        URL: /api/external-resources/doc_pages/
        """
        try:
            resources = ExternalResource.objects.filter(
                resource_type='doc_page'
            ).order_by('system_name', 'name')

            system_name = request.query_params.get('system_name', None)
            if system_name:
                resources = resources.filter(system_name__iexact=system_name)

            serializer = ExternalResourceListSerializer(resources, many=True)
            return Response({
                'count': resources.count(),
                'doc_pages': serializer.data,
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching doc pages",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)

    @action(detail=False, methods=['get'])
    def systems(self, request):
        """
        Get list of available documentation systems
        URL: /api/external-resources/systems/
        """
        try:
            systems = ExternalResource.objects.values_list(
                'system_name',
                flat=True
            ).distinct().order_by('system_name')

            return Response({
                'count': len(systems),
                'systems': list(systems),
            })
        except Exception as e:
            return Response({
                "error": "Internal server error occurred while fetching systems",
                "detail": str(e) if settings.DEBUG else "Please try again later",
            }, status=500)
