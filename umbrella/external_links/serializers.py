from rest_framework import serializers

from external_links.models import ExternalResource


class ExternalResourceSerializer(serializers.ModelSerializer):
    """
    Serializer for ExternalResource model
    """

    resource_type_display = serializers.CharField(source="get_resource_type_display", read_only=True)

    class Meta:
        model = ExternalResource
        fields = [
            "id",
            "resource_type",
            "resource_type_display",
            "system_name",
            "name",
            "url",
            "metadata",
        ]

    def validate_url(self, value):
        """
        Validate URL uniqueness
        """
        instance = self.instance
        url_query = ExternalResource.objects.filter(url=value)

        if instance:
            url_query = url_query.exclude(pk=instance.pk)

        if url_query.exists():
            existing = url_query.first()
            raise serializers.ValidationError(
                f"A resource with this URL already exists: {existing.name} ({existing.system_name})"
            )

        return value


class ExternalResourceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing external resources (excludes metadata)
    """

    resource_type_display = serializers.CharField(source="get_resource_type_display", read_only=True)

    class Meta:
        model = ExternalResource
        fields = [
            "id",
            "resource_type",
            "resource_type_display",
            "system_name",
            "name",
            "url",
        ]
