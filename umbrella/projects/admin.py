from django.contrib import admin

from .models import Project, ProjectMembership


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0
    autocomplete_fields = ("user",)
    fields = ("user", "role", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "project_leader", "description")
    search_fields = ("name", "description")
    autocomplete_fields = ("project_leader", "institutions", "contributors")
    # Groups are managed by projects.services; shown for reference only.
    readonly_fields = ("viewer_group", "editor_group")
    inlines = (ProjectMembershipInline,)
