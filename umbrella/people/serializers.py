"""DRF serializers for the people directory app."""

import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from people.models import Institution, Person

ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


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
