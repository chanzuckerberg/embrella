"""DRF serializers for the depositions submission.

Save model — shallow-nested autosave per wizard step:
  PATCH /depositions/[id]  -> deposition fields + authors_json
  PATCH /datasets/[id]     -> dataset fields + funding + session selection (nested, writable)
  PATCH /sessions/[id]     -> session + tiltseries/tomogram metadata + annotations (nested, writable;
                              annotations upserted by (copick_kind, copick_ref))
Method links have their own endpoint (avoids 2-level nesting), so they are read-only
when nested under an annotation.
"""

from rest_framework import serializers

from .models import (
    Dataset,
    DatasetFunding,
    Deposition,
    DepositionAnnotation,
    DepositionAnnotationMethodLink,
    DatasetJob,
    DepositionSession,
    TiltseriesMetadata,
    TomogramMetadata,
)
from .permissions import deposition_owner_id


def validate_authors_json(value):
    """Light shape check for the authors_json column on Deposition/Dataset.

    Expects a list of {author_id, author_list_order, is_primary, is_corresponding}.
    `author_id` soft-references people.Person — we validate the SHAPE only, not that
    the id exists. the soft-ref design intentionally avoids author lookups.
    """
    if not isinstance(value, list):
        raise serializers.ValidationError("authors_json must be a list of author entries.")
    for i, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise serializers.ValidationError(f"authors_json[{i}] must be an object.")
        author_id = entry.get("author_id")
        # bool is a subclass of int — reject True/False masquerading as an id.
        if not isinstance(author_id, int) or isinstance(author_id, bool):
            raise serializers.ValidationError(f"authors_json[{i}].author_id must be an integer.")
        order = entry.get("author_list_order")
        if order is not None and (not isinstance(order, int) or isinstance(order, bool)):
            raise serializers.ValidationError(f"authors_json[{i}].author_list_order must be an integer.")
        for flag in ("is_primary", "is_corresponding"):
            if flag in entry and not isinstance(entry[flag], bool):
                raise serializers.ValidationError(f"authors_json[{i}].{flag} must be a boolean.")
    return value


class DepositionAnnotationMethodLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositionAnnotationMethodLink
        fields = "__all__"


class DatasetFundingSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = DatasetFunding
        fields = ["id", "funding_agency_name", "grant_id"]


class TiltseriesMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiltseriesMetadata
        exclude = ["session"]
        read_only_fields = ["created_at", "updated_at"]


class TomogramMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TomogramMetadata
        exclude = ["session"]
        read_only_fields = ["created_at", "updated_at"]


class DepositionAnnotationSerializer(serializers.ModelSerializer):
    # method_links managed via their own endpoint -> read-only here
    method_links = DepositionAnnotationMethodLinkSerializer(many=True, read_only=True)

    class Meta:
        model = DepositionAnnotation
        exclude = ["session"]
        read_only_fields = ["created_at", "updated_at"]


class DatasetJobSerializer(serializers.ModelSerializer):
    """Read-only — job state is driven by the processors, never set via the API."""

    class Meta:
        model = DatasetJob
        fields = "__all__"


class DepositionSessionLinkSerializer(serializers.ModelSerializer):
    """Shallow session view used when nested under a Dataset (selection only — no metadata)."""

    id = serializers.IntegerField(required=False)

    class Meta:
        model = DepositionSession
        fields = [
            "id",
            "msi_session",
            "aretomo_run_name",
            "denoise_run_name",
            "subset_csv_path",
            "selected_copick_runs",
        ]


class DepositionSessionSerializer(serializers.ModelSerializer):
    """Full session view used at /sessions/[id] — writable metadata + annotations."""

    tiltseries_metadata = TiltseriesMetadataSerializer(required=False)
    tomogram_metadata = TomogramMetadataSerializer(required=False)
    annotations = DepositionAnnotationSerializer(many=True, required=False)

    class Meta:
        model = DepositionSession
        fields = "__all__"
        read_only_fields = [
            "dataset",
            "created_at",
            "updated_at",
            "last_autofill_at",
            "last_autofill_duration_seconds",
        ]

    def update(self, instance, validated_data):
        ts = validated_data.pop("tiltseries_metadata", None)
        tomo = validated_data.pop("tomogram_metadata", None)
        annotations = validated_data.pop("annotations", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ts is not None:
            TiltseriesMetadata.objects.update_or_create(session=instance, defaults=ts)
        if tomo is not None:
            TomogramMetadata.objects.update_or_create(session=instance, defaults=tomo)
        if annotations is not None:
            self._sync_annotations(instance, annotations)
        return instance

    def _sync_annotations(self, session, annotations):
        """Upsert annotations by (copick_kind, copick_ref); delete any no longer present."""
        seen = set()
        for ann in annotations:
            kind, ref = ann.get("copick_kind"), ann.get("copick_ref")
            seen.add((kind, ref))
            DepositionAnnotation.objects.update_or_create(
                session=session, copick_kind=kind, copick_ref=ref, defaults=ann
            )
        for existing in session.annotations.all():
            if (existing.copick_kind, existing.copick_ref) not in seen:
                existing.delete()


class DatasetSerializer(serializers.ModelSerializer):
    funding = DatasetFundingSerializer(many=True, required=False)
    sessions = DepositionSessionLinkSerializer(many=True, required=False)
    job = DatasetJobSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = "__all__"
        # dataset_id is server-reserved; status is written by the syncer; dates auto-managed.
        read_only_fields = ["dataset_id", "status", "created_at", "updated_at"]

    def get_is_owner(self, obj) -> bool:
        return _is_owner(self, obj)

    def validate_authors_json(self, value):
        return validate_authors_json(value)

    def create(self, validated_data):
        # Create is shallow by design (POST reserves the id; nested funding/sessions
        # arrive via PATCH), but handle them here too.
        funding = validated_data.pop("funding", None)
        sessions = validated_data.pop("sessions", None)

        dataset = Dataset.objects.create(**validated_data)

        if funding is not None:
            self._sync_funding(dataset, funding)
        if sessions is not None:
            self._sync_sessions(dataset, sessions)
        return dataset

    def update(self, instance, validated_data):
        funding = validated_data.pop("funding", None)
        sessions = validated_data.pop("sessions", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if funding is not None:
            self._sync_funding(instance, funding)
        if sessions is not None:
            self._sync_sessions(instance, sessions)
        return instance

    def _sync_funding(self, dataset, funding):
        seen = set()
        for row in funding:
            fid = row.pop("id", None)
            # Only reuse an id that actually belongs to THIS dataset; a stray/foreign
            # id falls through to create (never forces an explicit PK ).
            existing = dataset.funding.filter(id=fid).first() if fid else None
            if existing:
                for attr, value in row.items():
                    setattr(existing, attr, value)
                existing.save()
                obj = existing
            else:
                obj = DatasetFunding.objects.create(dataset=dataset, **row)
            seen.add(obj.id)
        dataset.funding.exclude(id__in=seen).delete()

    def _sync_sessions(self, dataset, sessions):
        """Create/update the session-selection links; delete deselected ones."""
        seen = set()
        for row in sessions:
            row.pop("id", None)
            msi_session = row.pop("msi_session", None)
            if msi_session is None:
                raise serializers.ValidationError(
                    {"sessions": "Each session entry requires msi_session."}
                )
            obj, _ = DepositionSession.objects.update_or_create(
                dataset=dataset, msi_session=msi_session, defaults=row
            )
            seen.add(obj.id)
        dataset.sessions.exclude(id__in=seen).delete()


def _is_owner(serializer, obj) -> bool:
    request = serializer.context.get("request")
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return False
    return deposition_owner_id(obj) == user.id


class DepositionSerializer(serializers.ModelSerializer):
    datasets = DatasetSerializer(many=True, read_only=True)
    submitter_username = serializers.CharField(source="submitter_user.username", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Deposition
        fields = "__all__"
        # deposition_id is server-reserved; submitter_user set from request.user.
        read_only_fields = ["deposition_id", "submitter_user", "created_at", "updated_at"]

    def get_is_owner(self, obj) -> bool:
        return _is_owner(self, obj)

    def validate_authors_json(self, value):
        return validate_authors_json(value)


class SubmissionDatasetSerializer(serializers.ModelSerializer):
    """Lightweight dataset row for the My Submissions list (GET /depositions/?scope=mine).
    """

    session_names = serializers.SerializerMethodField()
    session_count = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = ["id", "dataset_id", "title", "status", "updated_at", "session_count", "session_names", "type"]

    def get_session_names(self, obj) -> list[str]:
        sessions = sorted(
            (s for s in obj.sessions.all() if s.msi_session_id),
            key=lambda s: s.msi_session.name or "",
        )
        return [s.msi_session.name for s in sessions]

    def get_session_count(self, obj) -> int:
        return len(obj.sessions.all())

    def get_type(self, obj) -> str:
        has_tomograms = any(
            hasattr(s, "tiltseries_metadata") or hasattr(s, "tomogram_metadata")
            for s in obj.sessions.all()
        )
        has_annotations = any(a.is_selected for s in obj.sessions.all() for a in s.annotations.all())
        if has_annotations and not has_tomograms:
            return "Annotations only"
        return "Dataset" if has_annotations else "Tomos only"


class SubmissionDepositionSerializer(serializers.ModelSerializer):
    """Deposition group for the My Submissions list — lean, with datasets summarized."""

    datasets = SubmissionDatasetSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Deposition
        fields = ["id", "deposition_id", "title", "description", "updated_at", "datasets", "is_owner"]

    def get_is_owner(self, obj) -> bool:
        return _is_owner(self, obj)
