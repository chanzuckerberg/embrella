"""DRF ViewSet for images. Uploads and deletes go through each owner's API, e.g. cryo_grids."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from images import services
from images.constants import RENDITION_PARAM, Rendition
from images.models import Image
from images.permissions import ImagesEnabled
from images.serializers import ImageNotesSerializer, ImageSerializer

IMAGES_TAG = "Images"


class ImageViewSet(viewsets.GenericViewSet):
    """URL: /images/v1/images/"""

    queryset = Image.objects.select_related("uploaded_by")
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated, ImagesEnabled]

    @extend_schema(
        tags=[IMAGES_TAG],
        summary="Edit image notes",
        request=ImageNotesSerializer,
        responses=ImageSerializer,
    )
    def partial_update(self, request, pk=None):
        image = self.get_object()
        serializer = ImageNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.update_notes(image, serializer.validated_data["notes"])
        return Response(ImageSerializer(image).data)

    @extend_schema(
        tags=[IMAGES_TAG],
        summary="Get an image file",
        description="`thumb` and `preview` are WebP display copies; `original` downloads under its uploaded name.",
        parameters=[OpenApiParameter(RENDITION_PARAM, enum=[r.value for r in Rendition], default=Rendition.PREVIEW)],
        responses={(status.HTTP_200_OK, "image/*"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        try:
            rendition = Rendition(request.query_params.get(RENDITION_PARAM, Rendition.PREVIEW))
        except ValueError:
            choices = ", ".join(r.value for r in Rendition)
            return Response(
                {"detail": f"{RENDITION_PARAM} must be one of: {choices}."}, status=status.HTTP_400_BAD_REQUEST
            )

        return services.serve(self.get_object(), rendition)
