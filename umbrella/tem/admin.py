from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from stores.models import fill_place_holders
from stores.placeholders import placeholders_in

from .models import (
    SOFTWARE_PATH_ROLES,
    AtlasSession,
    CalibratedPixelSize,
    Camera,
    ImagingWorkflow,
    Magnification,
    Microscope,
    MsiSession,
    ScreenSessionGroup,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
    plan_replacement_map,
    resolve_software_file_pattern,
    resolve_software_path_type,
)

_RESOLVES_TO_CSS = mark_safe(
    "<style>"
    ".form-group.field-resolves_to > .row > label{display:none}"
    ".form-group.field-resolves_to > .row > div{flex:0 0 100%;max-width:100%}"
    "</style>"
)

# Register your models here.
admin.site.register(Microscope)
admin.site.register(Camera)
admin.site.register(Magnification)
admin.site.register(CalibratedPixelSize)
admin.site.register(ImagingWorkflow)


@admin.register(Software)
class SoftwareAdmin(admin.ModelAdmin):
    list_display = ("name", "version", *SOFTWARE_PATH_ROLES)
    search_fields = ("name", "version")
    autocomplete_fields = SOFTWARE_PATH_ROLES
    ordering = ("name", "version")
    fieldsets = (
        (None, {"fields": ("name", "version")}),
        (
            "Default path templates",
            {
                "fields": SOFTWARE_PATH_ROLES,
                "description": ("The template each role resolves to for every session plan using this software."),
            },
        ),
    )


class SessionPlanPathBindingInline(admin.TabularInline):
    model = SessionPlanPathBinding
    extra = 0
    autocomplete_fields = ("path_type", "file_pattern")
    # Both, not just the plural: the plural titles the tab, the singular the "Add another …"
    # button, which otherwise reads "Add another Session plan path binding".
    verbose_name = "path override"
    verbose_name_plural = "Path overrides"


@admin.register(SessionPlan)
class SessionPlanAdmin(admin.ModelAdmin):
    list_display = ("__str__", "scope", "camera", "software", "override_count")
    list_filter = ("scope", "camera", "software")
    inlines = (SessionPlanPathBindingInline,)
    readonly_fields = ("resolves_to",)
    fieldsets = (
        (None, {"fields": ("scope", "camera", "imaging_workflow", "software")}),
        (
            "Resolves to",
            {
                "fields": ("resolves_to",),
                "description": "What paths are resolved to.",
            },
        ),
    )

    @admin.display(description="overrides")
    def override_count(self, obj):
        return obj.path_bindings.filter(is_active=True, path_type__isnull=False).count() or ""

    @admin.display(description="")
    def resolves_to(self, obj):
        """Per role: the template, a substituted example, and where it came from.

        Pure display. Turns "which of these do I need to override?" into a glance --
        without it an operator opens a fresh plan, sees an empty inline, and cannot tell
        which roles the software even emits.
        """
        if obj is None or obj.pk is None:
            return "Save the plan first."
        example = {**plan_replacement_map(obj), "msi_session": "24nov10"}
        overridden = {b.role for b in obj.path_bindings.filter(is_active=True, path_type__isnull=False)}
        rows = []
        for role in SOFTWARE_PATH_ROLES:
            path_type = resolve_software_path_type(obj, role)
            if path_type is None:
                rows.append((role, "unset", "—", "—", "software does not produce this role"))
                continue
            resolved = fill_place_holders(path_type.overlay_path, example)
            leftover = placeholders_in(resolved)
            note = "unsubstituted: " + ", ".join(sorted("{%s}" % t for t in leftover)) if leftover else ""
            # The directory is only half the answer since the split -- without the pattern
            # the panel reads as if the filenames were lost.
            pattern = resolve_software_file_pattern(obj, role)
            rows.append(
                (
                    role,
                    "binding" if role in overridden else "software default",
                    resolved,
                    pattern.list_glob if pattern else "—",
                    note,
                )
            )
        # Bootstrap classes, not admin ones: jazzmin leaves a bare <table> unstyled, and
        # without fixed layout + break-all the paths overflow and push `note` off-screen.
        return format_html(
            '{}<table class="table table-sm" style="table-layout:fixed;width:100%">'
            '<colgroup><col style="width:6em"><col style="width:9em"><col>'
            '<col style="width:10em"><col style="width:12em"></colgroup>'
            "<tr><th>role</th><th>source</th><th>directory</th><th>files</th><th>note</th></tr>{}</table>",
            _RESOLVES_TO_CSS,
            format_html_join(
                "",
                "<tr><td><b>{}</b></td>"
                '<td style="white-space:nowrap">{}</td>'
                '<td><code style="word-break:break-all">{}</code></td>'
                '<td><code style="word-break:break-all">{}</code></td>'
                '<td style="word-break:break-all">{}</td></tr>',
                rows,
            ),
        )


@admin.register(MsiSession)
class MsiSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "project", "session_plan", "magnification", "created_at")
    list_filter = ("session_plan", "magnification")
    raw_id_fields = ("grid", "frames", "mdocs", "sums", "parents", "atlas", "atlas_session")


admin.site.register(ScreenSessionGroup)
admin.site.register(AtlasSession)
