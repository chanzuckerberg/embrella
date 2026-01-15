"""Admin interface for external documentation links."""
from django.contrib import admin
from .models import ExternalResource


@admin.register(ExternalResource)
class ExternalResourceAdmin(admin.ModelAdmin):
    """Admin interface for ExternalResource model."""

    list_display = ['name', 'system_name', 'resource_type', 'url']
    list_filter = ['resource_type', 'system_name']
    search_fields = ['name', 'url', 'system_name']
    fieldsets = (
        ('Basic Information', {
            'fields': ('resource_type', 'system_name', 'name', 'url')
        }),
        ('System-Specific Data', {
            'fields': ('metadata',),
            'classes': ('collapse',),
            'description': 'Optional JSON data for system-specific fields (e.g., space_id for Confluence)'
        }),
    )
