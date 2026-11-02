from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from images import services
from images.models import Image


@admin.register(Image)
class ImageAdmin(SimpleHistoryAdmin):
    list_display = ["original_name", "project", "uploaded_by", "created_at"]
    list_filter = ["project"]
    search_fields = ["original_name", "notes"]

    # Files and their metadata come from images.services.ingest; only notes are editable
    readonly_fields = [
        "id",
        "project",
        "original",
        "preview",
        "thumb",
        "original_name",
        "content_type",
        "size_bytes",
        "width",
        "height",
        "uploaded_by",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    # Through the service so files are removed with rows
    def delete_model(self, request, obj):
        services.delete(obj)

    def delete_queryset(self, request, queryset):
        for image in queryset:
            services.delete(image)
