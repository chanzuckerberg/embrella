from django import forms
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from stores import placeholders

from .models import Cluster, DataKind, FilePattern, Path, PathType

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


def _capture_group_help():
    """Render the file-scoped tokens as ready-to-paste capture groups.

    The same vocabulary as `_placeholder_help`, read the other way round: these are exactly
    the tokens a directory template may not substitute, so a FilePattern has to capture them.
    """
    groups = format_html_join(
        "",
        "<li><code>(?P&lt;{}&gt;...)</code> &mdash; {}</li>",
        ((p.name, p.notes) for p in placeholders.PLACEHOLDERS if p.scope == placeholders.FILE_SCOPED),
    )
    return format_html(
        "Matched against the basename alone, anchored with <code>^</code> and <code>$</code>."
        "<br><strong>Eligible capture groups</strong> &mdash; a group's name is the token it "
        "fills, so only these names are read by anything:<ul>{}</ul>"
        "Need one that is not listed? It has to be declared in "
        "<code>stores/placeholders/vocabulary.py</code> first &mdash; ask a developer. An "
        "unlisted name saves fine, but nothing will use it.",
        groups,
    )


# A single-line input holding code: monospace, and never spellchecked.
_CODE_INPUT_ATTRS = {
    "class": "vTextField form-control",
    "style": "font-family: monospace;",
    "spellcheck": "false",
}


def _as_code_field(form, name, help_html):
    """Style `name` as code and give it rendered help, if the form has that field."""
    field = form.base_fields.get(name)
    if not field:
        return

    field.help_text = help_html
    field.widget.attrs.update(_CODE_INPUT_ATTRS)


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


class _FilenameLines(forms.CharField):
    """One basename per line, stored as the JSON list the model field holds.

    The stored type is a list, but making an operator type JSON quoting to enter three
    filenames is a tax on the field that exists to make config easy to check.
    """

    widget = forms.Textarea(
        attrs={**_CODE_INPUT_ATTRS, "rows": 4, "style": "font-family: monospace; height: auto;"},
    )

    def prepare_value(self, value):
        return "\n".join(value) if isinstance(value, list) else value

    def to_python(self, value):
        if isinstance(value, list):
            return value
        return [line.strip() for line in (value or "").splitlines() if line.strip()]


class FilePatternForm(forms.ModelForm):
    sample_filenames = _FilenameLines(
        required=False,
        help_text="One real basename per line. Checked against the regex on save.",
    )

    class Meta:
        model = FilePattern
        fields = "__all__"


@admin.register(FilePattern)
class FilePatternAdmin(admin.ModelAdmin):
    form = FilePatternForm
    list_display = ("label", "data_kind", "list_glob", "regex")
    list_filter = ("data_kind",)
    search_fields = ("label", "regex", "list_glob")
    autocomplete_fields = ("data_kind",)
    readonly_fields = ("created_at",)
    ordering = ("data_kind__data_type", "label")
    fieldsets = (
        (
            None,
            {
                "fields": ("data_kind", "label", "list_glob", "sample_filenames", "regex", "notes", "created_at"),
                "description": (
                    "How to list and read the files in a directory. Paste real basenames into "
                    "Sample filenames first, then write the regex that matches them - it is "
                    "checked against them on save."
                ),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        _as_code_field(form, "regex", _capture_group_help())
        return form


@admin.register(PathType)
class PathTypeAdmin(admin.ModelAdmin):
    list_display = ("data_kind", "overlay_path", "cluster", "file_pattern")
    list_filter = ("cluster", "data_kind")
    search_fields = ("data_kind__data_type", "overlay_path")
    autocomplete_fields = ("data_kind", "cluster", "file_pattern")
    ordering = ("data_kind__data_type", "cluster")
    fieldsets = (
        (
            None,
            {
                "fields": ("data_kind", "overlay_path", "cluster", "file_pattern"),
                "description": (
                    "A <strong>directory</strong> template. Leave the cluster blank for the default that "
                    "serves every cluster; add a row naming a cluster only where that cluster differs. "
                    "The file pattern is the naming convention normally found here; a plan can override "
                    "it on its own binding."
                ),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        _as_code_field(form, "overlay_path", _placeholder_help())
        return form


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("cluster_id", "name", "http_base_url", "ssh_hostname", "ssh_port", "is_active", "is_default")
    list_editable = ("is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("cluster_id", "name", "ssh_hostname")
