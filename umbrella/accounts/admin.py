from django.contrib import admin

from .models import Profile, SystemFeatureFlag, UserClusterCredentials


@admin.register(SystemFeatureFlag)
class SystemFeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "description")
    list_editable = ("enabled",)  # toggle on/off straight from the list
    search_fields = ("name", "description")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "orcid_authenticated", "feature_flags_summary", "updated_at")
    search_fields = ("user__username", "user__email", "orcid_authenticated")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Feature flags")
    def feature_flags_summary(self, obj):
        flags = obj.feature_flags or {}
        if not flags:
            return "—"
        enabled = [name for name, value in flags.items() if value]
        summary = ", ".join(enabled) if enabled else "none on"
        return f"{len(enabled)}/{len(flags)} on: {summary}"


@admin.register(UserClusterCredentials)
class UserClusterCredentialsAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster", "username", "updated_at")
    list_filter = ("cluster",)
    search_fields = ("user__username", "user__email", "username")
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)
