from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from external_links.models import ExternalResource
from people.models import Institution, Person
from people.serializers import InstitutionSerializer, PersonSerializer
from rest_framework import serializers

from projects.models import Project, ProjectMembership, ProjectRole


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Read shape of a membership: ``{user_id, username, role}``."""

    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ["user_id", "username", "role"]


class MemberWriteSerializer(serializers.Serializer):
    """Payload for the members action: ``{user, role}``. Role is ignored on DELETE."""

    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    role = serializers.ChoiceField(choices=ProjectRole.choices, default=ProjectRole.VIEWER)


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for Project model
    """

    project_leader_name = serializers.SerializerMethodField(read_only=True)
    documentation_space_name = serializers.SerializerMethodField(read_only=True)
    documentation_space_url = serializers.SerializerMethodField(read_only=True)

    # Members change only through the members action (keeps role groups in sync).
    members = ProjectMemberSerializer(source="memberships", many=True, read_only=True)

    # Read: nested objects. Write: pass `institution_ids` / `contributor_ids`.
    institutions = InstitutionSerializer(many=True, read_only=True)
    institution_ids = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(),
        source="institutions",
        many=True,
        write_only=True,
        required=False,
    )
    contributors = PersonSerializer(many=True, read_only=True)
    contributor_ids = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="contributors",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "project_leader",
            "project_leader_name",
            "documentation_space",
            "documentation_space_name",
            "documentation_space_url",
            "members",
            "institutions",
            "institution_ids",
            "contributors",
            "contributor_ids",
        ]
        read_only_fields = ["id"]

    def get_project_leader_name(self, obj):
        """Get project leader's username"""
        if obj.project_leader:
            return obj.project_leader.username
        return None

    def get_documentation_space_name(self, obj):
        """Get documentation space name"""
        if obj.documentation_space:
            return obj.documentation_space.name
        return None

    def get_documentation_space_url(self, obj):
        """Get documentation space URL"""
        if obj.documentation_space:
            return obj.documentation_space.url
        return None

    def validate_name(self, value):
        """
        Validate that project name is unique and not empty
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Project name is required.")

        # Check for uniqueness (excluding current instance during update)
        instance = self.instance
        name_query = Project.objects.filter(name=value.strip())
        if instance:
            name_query = name_query.exclude(pk=instance.pk)
        if name_query.exists():
            raise serializers.ValidationError(f'A project with name "{value}" already exists.')

        return value.strip()

    def validate(self, data):
        """
        Custom validation for project creation
        """
        # Validate foreign keys exist if provided
        if "project_leader" in data and data["project_leader"] is not None:
            if not User.objects.filter(id=data["project_leader"].id).exists():
                raise serializers.ValidationError(
                    {
                        "project_leader": "Selected user does not exist.",
                    }
                )

        if "documentation_space" in data and data["documentation_space"] is not None:
            if not ExternalResource.objects.filter(id=data["documentation_space"].id).exists():
                raise serializers.ValidationError(
                    {
                        "documentation_space": "Selected documentation space does not exist.",
                    }
                )

        return data
