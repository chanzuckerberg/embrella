import re

from rest_framework import serializers

from tem.models import MsiSession


class MsiSessionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=20)
    session_plan_id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    grid_id = serializers.IntegerField()
    magnification_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_name(self, value):
        if re.search(r"[@_!#$%^&*()<>?/\\|}{~:\s]", value):
            raise serializers.ValidationError("Name cannot contain special characters or spaces.")
        if MsiSession.objects.filter(name=value).exists():
            raise serializers.ValidationError("Session name already exists.")
        return value


class SessionPlanOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ProjectOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class FormOptionsSerializer(serializers.Serializer):
    session_plans = SessionPlanOptionSerializer(many=True)
    projects = ProjectOptionSerializer(many=True)


class SuggestNameSerializer(serializers.Serializer):
    suggested_name = serializers.CharField()


class MagnificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nominal_mag = serializers.IntegerField()
    mode = serializers.CharField()
    index = serializers.IntegerField()
    scope__name = serializers.CharField()
    display = serializers.SerializerMethodField()

    def get_display(self, obj):
        return "%gkx (%s) (%s)" % (obj["nominal_mag"] / 1000, obj["mode"], obj["scope__name"])


class RolePathSerializer(serializers.Serializer):
    """Where one role's data lands, in the two halves that vary independently.

    `directory` is resolved and final; `pattern` is the filename glob expected in it. Both
    are shown in the created-session dialog, the operator's only verification surface.
    """

    directory = serializers.CharField(allow_null=True)
    pattern = serializers.CharField(allow_null=True)


class CreatedSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    project_name = serializers.CharField()
    grid_name = serializers.CharField()
    session_plan_name = serializers.CharField()
    magnification_display = serializers.CharField(allow_null=True)
    frames = RolePathSerializer()
    sums = RolePathSerializer()
    mdocs = RolePathSerializer()
    parents = RolePathSerializer()
    atlas = RolePathSerializer()
    legacy_url = serializers.CharField()
