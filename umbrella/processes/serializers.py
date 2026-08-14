"""
Read serializers for the storage-explorer API.
"""

from rest_framework import serializers

from processes.models import format_bytes


class StorageSessionRefSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class NamedRefSerializer(serializers.Serializer):
    """{id, name} for entities the frontend may deep-link to."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class UserRefSerializer(serializers.Serializer):
    """
    Session creator user.
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    fullName = serializers.CharField()


class StorageRunSerializer(serializers.Serializer):
    """
    a run directory, or the session root.
    """

    id = serializers.SerializerMethodField(help_text="Row id, namespaced so it cannot collide with a session row.")
    run = serializers.SerializerMethodField(
        help_text="{id, name}. id is null when no ProcRun record matches the directory on disk.",
    )
    software = serializers.CharField(
        help_text="On-disk directory name.",
    )
    procRunId = serializers.IntegerField(
        source="proc_run_id",
        allow_null=True,
        help_text="Null when no ProcRun record matches this directory.",
    )
    directoryCount = serializers.IntegerField(
        source="directory_count",
        help_text="Directories rolled up into this run, including nested ones.",
    )
    fileCount = serializers.IntegerField(source="file_count")
    totalSizeBytes = serializers.IntegerField(source="total_size_bytes")
    totalSizeDisplay = serializers.SerializerMethodField(
        help_text="Pre-formatted size. Sort on totalSizeBytes.",
    )
    lastModified = serializers.DateTimeField(
        source="newest_file_mtime",
        allow_null=True,
        help_text="Newest file mtime anywhere under this run.",
    )
    pathPrefix = serializers.CharField(
        source="path_prefix",
        help_text="Absolute directory this run covers. Pass as `path_prefix` to /processes/v1/directories/ to drill in.",
    )
    # Both attached by the viewset from StorageDecision; not model fields.
    status = serializers.CharField(help_text="unset, preserve, delete or review.")
    decidedAtPrefix = serializers.CharField(
        source="decided_at_prefix",
        allow_null=True,
        help_text="Path the decision was recorded against: equal to pathPrefix if its own, shorter if inherited, null if none.",
    )

    def get_id(self, obj) -> str:
        """
        Namespaced by the leaf pk.
        """
        return f"storagerun-{obj.pk}"

    def get_run(self, obj) -> dict:
        """
        {id, name} where id may be null.
        """
        return {"id": obj.proc_run_id, "name": obj.run_name or "(session root)"}

    def get_totalSizeDisplay(self, obj) -> str:
        return format_bytes(obj.total_size_bytes)


class StorageSessionSerializer(serializers.Serializer):
    """A session row with its run leaves nested for table expansion."""

    storageSession = serializers.SerializerMethodField()
    sessionName = serializers.CharField(source="session_name")
    registered = serializers.BooleanField(
        help_text="False when the directory name matches no MsiSession. The row still appears and is actionable.",
    )
    msiSessionId = serializers.IntegerField(
        source="msi_session_id",
        allow_null=True,
        help_text="Null when registered is false.",
    )
    user = serializers.SerializerMethodField(
        help_text="Who created the session record, not the microscope operator.",
    )
    project = serializers.SerializerMethodField(help_text="Null for an unregistered session.")
    fsOwner = serializers.CharField(
        source="fs_owner",
        allow_blank=True,
        help_text="Filesystem owner, which often differs from the session's user.",
    )
    cluster = serializers.CharField()
    softwareCount = serializers.IntegerField(
        source="software_count",
        help_text="Distinct software directories this session has data under.",
    )
    runCount = serializers.IntegerField(
        source="run_count",
        help_text="Run directories, excluding the session-root leaf shown in `runs` as '(session root)'.",
    )
    directoryCount = serializers.IntegerField(source="directory_count")
    fileCount = serializers.IntegerField(source="file_count")
    totalSizeBytes = serializers.IntegerField(
        source="total_size_bytes",
        help_text="Equals the sum of `runs`, including under a filter.",
    )
    totalSizeDisplay = serializers.SerializerMethodField(
        help_text="Pre-formatted size. Sort on totalSizeBytes.",
    )
    lastModified = serializers.DateTimeField(
        source="last_modified",
        allow_null=True,
        help_text="Newest file mtime anywhere in the session.",
    )
    status = serializers.CharField(
        help_text="Shared status of the session's runs, or 'mixed' when they disagree. 'mixed' is never stored.",
    )
    runs = StorageRunSerializer(many=True, help_text="Leaves for the client to group into a software tier.")

    def get_storageSession(self, obj) -> dict:
        return StorageSessionRefSerializer({"id": obj["session_name"], "name": obj["session_name"]}).data

    def get_user(self, obj) -> dict | None:
        if not obj.get("user_id"):
            return None
        return UserRefSerializer(
            {"id": obj["user_id"], "username": obj["username"], "fullName": obj["user_full_name"]},
        ).data

    def get_project(self, obj) -> dict | None:
        if not obj.get("project_id"):
            return None
        return NamedRefSerializer({"id": obj["project_id"], "name": obj["project_name"]}).data

    def get_totalSizeDisplay(self, obj) -> str:
        return format_bytes(obj["total_size_bytes"])
