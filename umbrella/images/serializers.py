from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from images.constants import RENDITION_PARAM, Rendition
from images.models import Image


class ImageSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source="uploaded_by.username", default=None, read_only=True)
    urls = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            "id",
            "notes",
            "original_name",
            "content_type",
            "size_bytes",
            "width",
            "height",
            "uploaded_by",
            "created_at",
            "urls",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_urls(self, image) -> dict[str, str]:
        """One URL per file, e.g. {"thumb": "/images/v1/images/<id>/file/?r=thumb", ...}."""
        base = reverse("images:image-file", args=[image.pk])
        return {rendition.value: f"{base}?{RENDITION_PARAM}={rendition.value}" for rendition in Rendition}


class ImageNotesSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=True, trim_whitespace=False)


class ImageUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    notes = serializers.CharField(allow_blank=True, required=False, default="")
