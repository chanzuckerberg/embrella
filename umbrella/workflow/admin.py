"""
Admin for processes.ParameterDefaults.

The "Parameters" panel is filled client-side (static/workflow/parameter_defaults_admin.js):
it re-resolves the cascade whenever a dimension select changes, so the operator sees what
each parameter would be *without* this row and can pull single keys into `values`.
"""

import json

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from processes.models import ParameterDefaults, ProcSoftware

from workflow.defaults import check_value_type
from workflow.processors import get_processor

VALUES_HELP = (
    'JSON object, e.g. {"tilt_axis": 85.3, "frame_dose": null}. '
    "Keys must be parameters of the processor schema (see the Parameters panel). "
    "null clears the schema default and makes the user fill the field in. "
    "Set only the keys this row is meant to change; everything else keeps cascading."
)

_PANEL_CSS = mark_safe(
    "<style>"
    ".form-group.field-schema_keys > .row > label{display:none}"
    ".form-group.field-schema_keys > .row > div{flex:0 0 100%;max-width:100%}"
    "</style>"
)

# URL placeholder the JS swaps for the processor name; reverse() needs a real value.
_NAME_TOKEN = "__NAME__"


def _schema_properties(proc_software):
    """Schema properties for a ProcSoftware, or a ValidationError naming the problem."""
    try:
        processor = get_processor(proc_software.processor_class or "")
    except ValueError:
        raise forms.ValidationError(
            {"proc_software": "No registered processor for %r." % proc_software.processor_class}
        )
    return processor.get_parameter_schema().get("properties", {})


class ParameterDefaultsForm(forms.ModelForm):
    class Meta:
        model = ParameterDefaults
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        proc_software = cleaned.get("proc_software")
        values = cleaned.get("values")
        if proc_software is None or not isinstance(values, dict):
            return cleaned

        props = _schema_properties(proc_software)

        unknown = sorted(key for key in values if key not in props)
        if unknown:
            self.add_error(
                "values",
                "Unknown parameter(s): %s. Allowed: %s." % (", ".join(unknown), ", ".join(sorted(props))),
            )

        wrong_type = [
            "%s: %s" % (key, problem)
            for key, value in values.items()
            if key in props and (problem := check_value_type(value, props[key]))
        ]
        if wrong_type:
            self.add_error("values", "; ".join(wrong_type))

        return cleaned


@admin.register(ParameterDefaults)
class ParameterDefaultsAdmin(admin.ModelAdmin):
    form = ParameterDefaultsForm
    list_display = ("proc_software", "software", "scope", "cluster", "key_count", "is_active")
    list_filter = ("proc_software", "software", "scope", "cluster", "is_active")
    readonly_fields = ("schema_keys",)
    fieldsets = (
        (
            "Applies to",
            {
                "fields": ("proc_software", "software", "scope", "cluster", "is_active"),
                # Jazzmin escapes fieldset descriptions: plain text only.
                "description": (
                    "Blank dimensions match anything. When several rows match a launch, the more "
                    "specific one wins key by key: software < scope < scope+software < "
                    "cluster < cluster+software < cluster+scope < all three."
                ),
            },
        ),
        (
            "Parameters",
            {
                "fields": ("schema_keys",),
                "description": (
                    "What each parameter resolves to for the dimensions above, ignoring this row. "
                    "Use 'Add to Values' to copy one into the Values tab, then edit it there."
                ),
            },
        ),
        ("Values", {"fields": ("values", "notes")}),
    )

    class Media:
        js = ("workflow/parameter_defaults_admin.js",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "values" in form.base_fields:
            form.base_fields["values"].help_text = VALUES_HELP
        return form

    @admin.display(description="keys")
    def key_count(self, obj):
        return len(obj.values) if isinstance(obj.values, dict) else ""

    @admin.display(description="")
    def schema_keys(self, obj):
        """Mount point for the JS panel; the data attributes are everything it needs."""
        processors = dict(ProcSoftware.objects.filter(active=True).values_list("pk", "processor_class"))
        return format_html(
            '{}<div id="parameter-defaults-panel" data-row-pk="{}" data-processors="{}" '
            'data-defaults-url="{}" data-schema-url="{}">Pick a processor above.</div>',
            _PANEL_CSS,
            obj.pk if obj is not None and obj.pk is not None else "",
            json.dumps(processors),
            reverse("workflow:get_processor_defaults", args=[_NAME_TOKEN]),
            reverse("workflow:get_processor_schema", args=[_NAME_TOKEN]),
        )
