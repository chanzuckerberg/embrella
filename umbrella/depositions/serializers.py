"""DRF serializers for the depositions submission.

Save model — shallow-nested autosave per wizard step:
  PATCH /depositions/[id]  -> deposition fields + authors_json
  PATCH /datasets/[id]     -> dataset fields + funding + session selection (nested, writable)
  PATCH /sessions/[id]     -> session + tiltseries/tomogram metadata + annotations (nested, writable;
                              annotations upserted by (copick_kind, copick_ref); each annotation's
                              method_links written inline, upserted by id)
"""

from cryo_grids.models import Sample
from django.db.models import prefetch_related_objects
from rest_framework import serializers

from .models import (
    Dataset,
    DatasetFunding,
    DatasetJob,
    Deposition,
    DepositionAnnotation,
    DepositionAnnotationMethodLink,
    DepositionSession,
    TiltseriesMetadata,
    TomogramMetadata,
)
from .permissions import deposition_owner_id


def validate_authors_json(value):
    """Shape-check authors_json and allow partial rows for autosave."""
    if not isinstance(value, list):
        raise serializers.ValidationError("authors_json must be a list of author entries.")
    int_fields = ("author_id", "author_list_order")
    bool_fields = ("is_primary", "is_corresponding")
    str_fields = ("full_name", "affiliation", "identifier_type", "orcid")
    for i, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise serializers.ValidationError(f"authors_json[{i}] must be an object.")
        for f in int_fields:
            v = entry.get(f)
            # bool is a subclass of int — reject True/False masquerading as a number.
            if v is not None and (not isinstance(v, int) or isinstance(v, bool)):
                raise serializers.ValidationError(f"authors_json[{i}].{f} must be an integer.")
        for f in bool_fields:
            if f in entry and not isinstance(entry[f], bool):
                raise serializers.ValidationError(f"authors_json[{i}].{f} must be a boolean.")
        for f in str_fields:
            if f in entry and not isinstance(entry[f], str):
                raise serializers.ValidationError(f"authors_json[{i}].{f} must be a string.")
    return value


def validate_selected_copick_runs(value):
    """Shape-check selected_copick_runs: a list of unique, non-empty run-name strings."""
    if not isinstance(value, list):
        raise serializers.ValidationError("selected_copick_runs must be a list of run-name strings.")
    seen = set()
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise serializers.ValidationError(f"selected_copick_runs[{i}] must be a non-empty string (run name).")
        if item in seen:
            raise serializers.ValidationError(f"Duplicate copick run '{item}' in selected_copick_runs.")
        seen.add(item)
    return value


class NestedMethodLinkSerializer(serializers.ModelSerializer):
    """Method links written inline under an annotation - the FK is set by the parent sync."""

    id = serializers.IntegerField(required=False)

    class Meta:
        model = DepositionAnnotationMethodLink
        fields = ["id", "link_type", "link", "custom_name"]


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
    method_links = NestedMethodLinkSerializer(many=True, required=False)

    class Meta:
        model = DepositionAnnotation
        exclude = ["session"]
        read_only_fields = ["created_at", "updated_at"]


class DatasetJobSerializer(serializers.ModelSerializer):
    """Read-only — job state is set by processors, not the API."""

    class Meta:
        model = DatasetJob
        fields = "__all__"


class DepositionSessionLinkSerializer(serializers.ModelSerializer):
    """Shallow session selection nested under Dataset.

    Metadata + annotations are read-only here so the wizard can reload saved tiltseries/tomogram
    values and annotation metadata (incl. method_links) on reopen. Writes go through PATCH /sessions/[id].
    """

    id = serializers.IntegerField(required=False)
    msi_session_name = serializers.CharField(source="msi_session.name", read_only=True)
    tiltseries_metadata = TiltseriesMetadataSerializer(read_only=True)
    tomogram_metadata = TomogramMetadataSerializer(many=True, read_only=True)
    annotations = DepositionAnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = DepositionSession
        fields = [
            "id",
            "msi_session",
            "msi_session_name",
            "aretomo_run_name",
            "denoise_run_name",
            "subset_csv_path",
            "subset_selection",
            "subset_filename",
            "selected_copick_runs",
            "tiltseries_metadata",
            "tomogram_metadata",
            "annotations",
            "last_autofill_at",
        ]
        read_only_fields = ["last_autofill_at"]

    def validate_selected_copick_runs(self, value):
        return validate_selected_copick_runs(value)


class DepositionSessionSerializer(serializers.ModelSerializer):
    """Full /sessions/[id] view — writable metadata + annotations."""

    tiltseries_metadata = TiltseriesMetadataSerializer(required=False)
    tomogram_metadata = TomogramMetadataSerializer(many=True, required=False)
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

    def validate_tomogram_metadata(self, value):
        """Each tomogram must have a valid, unique flavor (denoised/filtered) — the sync upserts by it."""
        valid = {"denoised", "filtered"}
        seen = set()
        for i, tomo in enumerate(value):
            flavor = tomo.get("flavor")
            if flavor not in valid:
                raise serializers.ValidationError(f"tomogram_metadata[{i}].flavor must be one of {sorted(valid)}.")
            if flavor in seen:
                raise serializers.ValidationError(f"Duplicate tomogram flavor '{flavor}'.")
            seen.add(flavor)
        return value

    def validate_selected_copick_runs(self, value):
        return validate_selected_copick_runs(value)

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
            self._sync_tomograms(instance, tomo)
        if annotations is not None:
            self._sync_annotations(instance, annotations)
        prefetch_related_objects([instance], "annotations__method_links")
        return instance

    def _sync_tomograms(self, session, tomograms):
        """Sync tomograms by flavor (denoised/filtered)."""
        seen = set()
        for tomo in tomograms:
            flavor = tomo.get("flavor", "")
            seen.add(flavor)
            TomogramMetadata.objects.update_or_create(session=session, flavor=flavor, defaults=tomo)
        for existing in session.tomogram_metadata.all():
            if existing.flavor not in seen:
                existing.delete()

    def _sync_annotations(self, session, annotations):
        """Upsert annotations by (copick_kind, copick_ref); drop removed ones."""
        seen = set()
        for ann in annotations:
            links = ann.pop("method_links", None)
            kind, ref = ann.get("copick_kind"), ann.get("copick_ref")
            seen.add((kind, ref))
            annotation, _ = DepositionAnnotation.objects.update_or_create(
                session=session, copick_kind=kind, copick_ref=ref, defaults=ann
            )
            if links is not None:
                self._sync_method_links(annotation, links)
        for existing in session.annotations.all():
            if (existing.copick_kind, existing.copick_ref) not in seen:
                existing.delete()

    def _sync_method_links(self, annotation, links):
        """Upsert method links by id; drop removed ones. New rows (no id) are created."""
        seen = set()
        for link in links:
            fid = link.pop("id", None)
            # Reuse id only if it belongs to this annotation, otherwise create new.
            existing = annotation.method_links.filter(id=fid).first() if fid else None
            if existing:
                for attr, value in link.items():
                    setattr(existing, attr, value)
                existing.save()
                obj = existing
            else:
                obj = DepositionAnnotationMethodLink.objects.create(annotation=annotation, **link)
            seen.add(obj.id)
        annotation.method_links.exclude(id__in=seen).delete()


class DatasetSampleSerializer(serializers.ModelSerializer):
    """Nested writable cryo_grids.Sample fields. Sample.name is auto-set, cell-component id is `ontology`."""

    class Meta:
        model = Sample
        fields = [
            "sample_type",
            "organism_name",
            "organism_taxid",
            "tissue_name",
            "tissue_id",
            "cell_name",
            "cell_type_id",
            "cell_strain_name",
            "cell_strain_id",
            "cell_component_name",
            "ontology",
            "development_stage_name",
            "development_stage_ontology_id",
            "disease_name",
            "disease_ontology_id",
        ]


class DatasetSerializer(serializers.ModelSerializer):
    funding = DatasetFundingSerializer(many=True, required=False)
    sessions = DepositionSessionLinkSerializer(many=True, required=False)
    sample = DatasetSampleSerializer(required=False)
    job = DatasetJobSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = "__all__"
        # dataset_id reserved; status/dates set by syncer/system.
        read_only_fields = ["dataset_id", "status", "created_at", "updated_at"]

    def get_is_owner(self, obj) -> bool:
        return _is_owner(self, obj)

    def validate_authors_json(self, value):
        return validate_authors_json(value)

    def create(self, validated_data):
        # Nested funding/sessions/sample usually come via PATCH, handle them on create too.
        funding = validated_data.pop("funding", None)
        sessions = validated_data.pop("sessions", None)
        sample = validated_data.pop("sample", None)

        dataset = Dataset.objects.create(**validated_data)

        if sample is not None:
            self._sync_sample(dataset, sample)
        if funding is not None:
            self._sync_funding(dataset, funding)
        if sessions is not None:
            self._sync_sessions(dataset, sessions)
        return dataset

    def update(self, instance, validated_data):
        funding = validated_data.pop("funding", None)
        sessions = validated_data.pop("sessions", None)
        sample = validated_data.pop("sample", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if sample is not None:
            self._sync_sample(instance, sample)
        if funding is not None:
            self._sync_funding(instance, funding)
        if sessions is not None:
            self._sync_sessions(instance, sessions)
        return instance

    def _sync_sample(self, dataset, sample_data):
        """Update a deposition-owned Sample only (name=deposition-dataset-<id>), never mutate shared grid samples."""
        owned_name = f"deposition-dataset-{dataset.id}"
        sample = dataset.sample
        if sample is None or sample.name != owned_name:
            sample, _ = Sample.objects.get_or_create(name=owned_name)
            dataset.sample = sample
            dataset.save(update_fields=["sample"])
        for attr, value in sample_data.items():
            setattr(sample, attr, value)
        sample.save()

    def _sync_funding(self, dataset, funding):
        seen = set()
        for row in funding:
            fid = row.pop("id", None)
            # Reuse id only if it belongs to this dataset, otherwise create new.
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
        """Upsert session links by msi_session, drop deselected ones."""
        seen = set()
        for row in sessions:
            row.pop("id", None)
            msi_session = row.pop("msi_session", None)
            if msi_session is None:
                raise serializers.ValidationError({"sessions": "Each session entry requires msi_session."})
            obj, _ = DepositionSession.objects.update_or_create(dataset=dataset, msi_session=msi_session, defaults=row)
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
    """Lean dataset row for My Submissions list."""

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
            hasattr(s, "tiltseries_metadata") or s.tomogram_metadata.exists() for s in obj.sessions.all()
        )
        has_annotations = any(a.is_selected for s in obj.sessions.all() for a in s.annotations.all())
        if has_annotations and not has_tomograms:
            return "Annotations only"
        return "Dataset" if has_annotations else "Tomos only"


class SubmissionDepositionSerializer(serializers.ModelSerializer):
    """Deposition group for My Submissions list."""

    datasets = SubmissionDatasetSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Deposition
        fields = ["id", "deposition_id", "title", "description", "updated_at", "datasets", "is_owner"]

    def get_is_owner(self, obj) -> bool:
        return _is_owner(self, obj)
