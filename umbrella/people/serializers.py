"""DRF serializers for the people directory app."""

import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from people.models import Institution, Person

ORCID_RE = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "ror_id",
            "address",
            "city",
            "country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PersonSerializer(serializers.ModelSerializer):
    orcid = serializers.CharField(
        max_length=19,
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[UniqueValidator(queryset=Person.objects.all())],
    )
    # Read: the full institution is nested inline. Write: pass `institution_id`.
    institution = InstitutionSerializer(read_only=True)
    institution_id = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(),
        source="institution",
        write_only=True,
        required=False,
        allow_null=True,
    )
    affiliation = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "user",
            "orcid",
            "given_name",
            "family_name",
            "contact_email",
            "institution",
            "institution_id",
            "affiliation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_orcid(self, value):
        """Normalize blank ORCID to NULL (so records without one don't collide) and validate format."""
        if value in (None, ""):
            return None
        value = value.strip()
        if not ORCID_RE.match(value):
            raise serializers.ValidationError("ORCID iD must be formatted as xxxx-xxxx-xxxx-xxxx.")
        return value

    def _resolve_affiliation(self, validated_data):
        """Map the convenience `affiliation` string to `Person.institution`.

        A blank/empty affiliation clears the institution; otherwise it is matched
        by exact name (or created). Only applied when `affiliation` was supplied,
        so it never clobbers an explicit `institution_id`.
        """
        if "affiliation" not in validated_data:
            return
        name = (validated_data.pop("affiliation") or "").strip()
        if not name:
            validated_data["institution"] = None
            return
        institution = Institution.objects.filter(name=name).first()
        if institution is None:
            institution = Institution.objects.create(name=name)
        validated_data["institution"] = institution

    def create(self, validated_data):
        self._resolve_affiliation(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._resolve_affiliation(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["affiliation"] = instance.institution.name if instance.institution else None
        return data
