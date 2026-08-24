from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from stores import placeholders

from .models import Cluster, DataKind, Path, PathType

admin.site.register(Path)


def _placeholder_help():
    """Render the token vocabulary into field help text.

    Generated from `stores.placeholders`, the same module the save-time validator checks
    against, so the documentation and the rule cannot disagree.

    The tokens contain braces, so every dynamic value goes through format_html_join as an
    *argument* -- interpolating them into a format string makes `{scope}` a KeyError.
    """
    rows = []
    for scope, heading, note in (
        (placeholders.SESSION_SCOPED, "Substituted here", ""),
        (
            placeholders.FILE_SCOPED,
            "NOT valid in a directory template",
            mark_safe(  # noqa: S308 - a constant in this module, not user input
                " &mdash; these identify a file <em>within</em> the directory. "
                "Use a named capture group in a File pattern instead."
            ),
        ),
    ):
        lines = format_html_join(
            "",
            "<li><code>{}</code> &mdash; {}</li>",
            (
                (p.token, p.source + (f" ({p.notes})" if p.notes else ""))
                for p in placeholders.PLACEHOLDERS
                if p.scope == scope
            ),
        )
        rows.append(format_html("<strong>{}</strong>{}<ul>{}</ul>", heading, note, lines))
    return mark_safe("".join(rows))  # noqa: S308 - each row already escaped above


MAX_TEMPLATES_SHOWN = 3


@admin.register(DataKind)
class DataKindAdmin(admin.ModelAdmin):
    list_display = ("data_type", "templates")
    search_fields = ("data_type",)
    ordering = ("data_type",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("pathtype_set")

    @admin.display(description="path types")
    def templates(self, obj):
        paths = [pt.overlay_path for pt in obj.pathtype_set.all()]
        if not paths:
            return "—"
        shown = format_html_join(
            mark_safe("<br>"),  # noqa: S308 - a literal separator
            "{}",
            ((p,) for p in paths[:MAX_TEMPLATES_SHOWN]),
        )
        if len(paths) <= MAX_TEMPLATES_SHOWN:
            return shown
        return format_html("{}<br>… and {} more", shown, len(paths) - MAX_TEMPLATES_SHOWN)


@admin.register(PathType)
class PathTypeAdmin(admin.ModelAdmin):
    list_display = ("data_kind", "overlay_path", "cluster")
    list_filter = ("cluster", "data_kind")
    search_fields = ("data_kind__data_type", "overlay_path")
    autocomplete_fields = ("data_kind", "cluster")
    ordering = ("data_kind__data_type", "cluster")
    fieldsets = (
        (
            None,
            {
                "fields": ("data_kind", "overlay_path", "cluster"),
                "description": (
                    "A <strong>directory</strong> template. Leave the cluster blank for the default that "
                    "serves every cluster; add a row naming a cluster only where that cluster differs."
                ),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "overlay_path" in form.base_fields:
            field = form.base_fields["overlay_path"]
            field.help_text = _placeholder_help()
            field.widget.attrs.update(
                {
                    "class": "vTextField form-control",
                    "style": "font-family: monospace;",
                    "spellcheck": "false",
                }
            )
        return form


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("cluster_id", "name", "http_base_url", "ssh_hostname", "ssh_port", "is_active", "is_default")
    list_editable = ("is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("cluster_id", "name", "ssh_hostname")
