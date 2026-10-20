from rest_framework import serializers

from timeline.types import EntryKind, Subject

# Referenced by SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES to name the schema enums
SUBJECT_CHOICES = [s.value for s in Subject]
KIND_CHOICES = [k.value for k in EntryKind]


class TimelineEntrySerializer(serializers.Serializer):
    at = serializers.DateTimeField(help_text="When it happened")
    subject = serializers.ChoiceField(
        choices=SUBJECT_CHOICES, help_text="What the entry is about: the grid or one of its sessions / runs"
    )
    subject_id = serializers.IntegerField(help_text="Id of the subject (grid, MSI session or proc run)")
    kind = serializers.ChoiceField(choices=KIND_CHOICES, help_text="Action type")
    summary = serializers.CharField(
        help_text='Human-readable line, e.g. "Grid moved: BoxA position 1 to BoxB position 2"'
    )
    user = serializers.CharField(allow_null=True, help_text="Username of who did it; null when unknown")
    detail = serializers.JSONField(help_text="Kind-specific extras, e.g. changed fields, label color, move from / to")
