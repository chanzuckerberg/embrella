"""
Read serializers for the session-overview API.

TODO: consolidate tem/api/serializers.py with this file
"""

from rest_framework import serializers


class SessionRefSerializer(serializers.Serializer):
    """Primary entity for a row -- EntityTable derives the row id from `session.id`."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class NamedRefSerializer(serializers.Serializer):
    """{id, name} for entities the frontend may deep-link to (project, grid)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class UserRefSerializer(serializers.Serializer):
    """
    Session user.

    This is MsiSession.user, which create_session sets to request.user.
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    fullName = serializers.CharField()


class ProcRunSubRowSerializer(serializers.Serializer):
    """
    Run details
    """

    id = serializers.SerializerMethodField()
    run = serializers.SerializerMethodField()
    planName = serializers.SerializerMethodField()
    planLabel = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    def get_id(self, obj) -> str:
        return f"run-{obj.pk}"

    def get_run(self, obj) -> dict:
        return {"id": obj.pk, "name": obj.name}

    def get_planName(self, obj) -> str:
        return obj.proc_plan.name

    def get_planLabel(self, obj) -> str:
        """Display name from ProcPlan.label"""
        return obj.proc_plan.label


class MsiSessionOverviewSerializer(serializers.Serializer):
    """A session row with its runs nested for table expansion."""

    session = serializers.SerializerMethodField()
    sessionDate = serializers.DateTimeField(source="created_at")
    user = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    scope = serializers.CharField(source="session_plan.scope.name")
    workflow = serializers.CharField(source="session_plan.imaging_workflow.workflow")
    grid = serializers.SerializerMethodField()
    runCount = serializers.IntegerField(source="run_count")
    processingSoftware = serializers.SerializerMethodField()
    reviewCount = serializers.IntegerField(source="review_count")
    lastRunAt = serializers.DateTimeField(source="last_run_at", allow_null=True)
    runs = serializers.SerializerMethodField()

    def get_session(self, obj) -> dict:
        return SessionRefSerializer({"id": obj.pk, "name": obj.name}).data

    def get_user(self, obj) -> dict | None:
        if not obj.user:
            return None
        return UserRefSerializer(
            {"id": obj.user.pk, "username": obj.user.username, "fullName": _display_name(obj.user)},
        ).data

    def get_project(self, obj) -> dict | None:
        if not obj.project:
            return None
        return NamedRefSerializer({"id": obj.project.pk, "name": obj.project.name}).data

    def get_grid(self, obj) -> dict | None:
        if not obj.grid:
            return None
        return NamedRefSerializer({"id": obj.grid.pk, "name": obj.grid.name}).data

    def get_processingSoftware(self, obj) -> list[str]:
        """
        Distinct plan labels across the session's runs.
        """
        return sorted({run.proc_plan.label for run in obj.overview_runs})

    def get_runs(self, obj) -> list[dict]:
        return ProcRunSubRowSerializer(obj.overview_runs, many=True).data


def _display_name(user) -> str:
    """
    Human-readable name
    """
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username.split("@")[0]
