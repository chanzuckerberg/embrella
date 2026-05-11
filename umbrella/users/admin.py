from django.contrib import admin

from .models import UserClusterCredentials


@admin.register(UserClusterCredentials)
class UserClusterCredentialsAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "username", "updated_at")
    list_filter = ("cluster",)
    search_fields = ("user__username", "user__email", "username")
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)
