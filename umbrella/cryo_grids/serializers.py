"""
DRF serializers for the cryo_grids app.

Contains serializers for cryo-EM grid storage models including Pucks, Canes,
CryoGridBoxes, and CryoGrids.
"""

from django.contrib.auth.models import User
from django.utils import timezone as django_timezone
from external_links.models import ExternalResource
from projects.models import Project
from rest_framework import serializers
from umbrella.choices import PUCK_COLORS

from cryo_grids.models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    Label,
    PlungeFreezingSession,
    Puck,
    Sample,
    Specimen,
)


class LabelSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Label
        fields = ["id", "name", "color", "created_by", "created_by_name", "created_at"]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at"]


class PuckSerializer(serializers.ModelSerializer):
    """
    Serializer for Puck model with essential fields
    """

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Puck
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "position_in_cane",
            "max_boxes",
            "user",
            "user_name",
            "cane",
        ]
        validators = []

    def validate(self, data):
        """
        Custom validation for puck creation/update
        """
        # Check for unique name + color combination
        name = data.get("name")
        color = data.get("color")
        cane = data.get("cane")
        position_in_cane = data.get("position_in_cane")

        # Get instance for update operations
        instance = self.instance

        # Validate unique name+color
        if name and color:
            puck_query = Puck.objects.filter(name=name, color=color)
            if instance:
                puck_query = puck_query.exclude(pk=instance.pk)
            if puck_query.exists():
                color_display = dict(PUCK_COLORS).get(color, color)
                raise serializers.ValidationError(
                    {
                        "name": f'A puck with name "CZII-0{name}" and color "{color_display}" already exists.',
                    }
                )

        # Validate unique cane+position
        if cane and position_in_cane:
            position_query = Puck.objects.filter(cane=cane, position_in_cane=position_in_cane)
            if instance:
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError(
                    {
                        "position_in_cane": f"Position {position_in_cane} in this cane is already occupied.",
                    }
                )

        return data

    def create(self, validated_data):
        """
        Create and return a new Puck instance
        """
        return Puck.objects.create(**validated_data)


class CryoGridBoxSerializer(serializers.ModelSerializer):
    """
    Serializer for CryoGridBox model
    """

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    numbering_display = serializers.CharField(source="get_numbering_display", read_only=True)
    puck_user = serializers.CharField(source="puck.user.username", read_only=True)

    class Meta:
        model = CryoGridBox
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "numbering",
            "numbering_display",
            "position_in_puck",
            "max_grids",
            "puck",
            "puck_user",
        ]
        validators = []  # disables default validators
        extra_kwargs = {
            "name": {"validators": []},  # to disable unique validator on name field
        }

    def validate(self, data):
        """
        Custom validation for grid box creation/update
        """
        instance = self.instance

        # For updates, use existing values if not provided in data (partial update support)
        if instance:
            name = data.get("name", instance.name)
            puck = data.get("puck", instance.puck)
            position_in_puck = data.get("position_in_puck", instance.position_in_puck)
        else:
            # For creation, get from data only
            name = data.get("name")
            puck = data.get("puck")
            position_in_puck = data.get("position_in_puck")

        # Validate unique constraint on name + puck + position_in_puck
        if name and puck and position_in_puck:
            name_query = CryoGridBox.objects.filter(
                puck=puck,
                position_in_puck=position_in_puck,
                name=name,
            )
            if instance:  # If updating, exclude current instance
                name_query = name_query.exclude(pk=instance.pk)
            if name_query.exists():
                raise serializers.ValidationError(
                    {
                        "name": f'A grid box with name "{name}" at position {position_in_puck} in this puck already exists.',
                    }
                )

        # Validate unique constraint on puck + position_in_puck
        if puck and position_in_puck:
            position_query = CryoGridBox.objects.filter(
                puck=puck,
                position_in_puck=position_in_puck,
            )
            if instance:  # If updating, exclude current instance
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError(
                    {
                        "position_in_puck": f"Position {position_in_puck} in this puck is already occupied.",
                    }
                )

        return data


class GridLabelInBoxSerializer(serializers.ModelSerializer):
    """Minimal label serializer for grids nested inside a grid box."""

    class Meta:
        model = Label
        fields = ["id", "name", "color"]


class GridInBoxSerializer(serializers.ModelSerializer):
    """Lightweight serializer for grids nested inside a grid box."""

    user_name = serializers.CharField(source="user.username", read_only=True, default=None)
    specimen_samples = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="intended_project.name", read_only=True, default=None)
    labels = GridLabelInBoxSerializer(many=True, read_only=True)

    class Meta:
        model = CryoGrid
        fields = [
            "id",
            "name",
            "position_in_box",
            "clipped",
            "trashed",
            "notes",
            "user_name",
            "specimen_samples",
            "project_name",
            "labels",
            "create_on",
        ]

    def get_specimen_samples(self, obj):
        if not obj.specimen:
            return []
        return [sample.name for sample in obj.specimen.samples.all()]


class CryoGridBoxListSerializer(serializers.ModelSerializer):
    """Serializer for grid box list view with nested grids."""

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    numbering_display = serializers.CharField(source="get_numbering_display", read_only=True)
    puck_name = serializers.CharField(source="puck.name", read_only=True, default=None)
    puck_user = serializers.CharField(source="puck.user.username", read_only=True, default=None)
    grid_count = serializers.IntegerField(read_only=True)
    grids = GridInBoxSerializer(source="cryogrid_set", many=True, read_only=True)

    class Meta:
        model = CryoGridBox
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "numbering",
            "numbering_display",
            "position_in_puck",
            "max_grids",
            "puck",
            "puck_name",
            "puck_user",
            "grid_count",
            "grids",
        ]


class GridBoxInPuckSerializer(serializers.ModelSerializer):
    """Serializer for grid boxes nested inside a puck, with nested grids."""

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    numbering_display = serializers.CharField(source="get_numbering_display", read_only=True)
    grid_count = serializers.IntegerField(read_only=True)
    grids = GridInBoxSerializer(source="cryogrid_set", many=True, read_only=True)

    class Meta:
        model = CryoGridBox
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "numbering",
            "numbering_display",
            "position_in_puck",
            "max_grids",
            "grid_count",
            "grids",
        ]


class PuckListSerializer(serializers.ModelSerializer):
    """Serializer for puck list view with nested grid boxes and grids."""

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    cane_name = serializers.CharField(source="cane.name", read_only=True, default=None)
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)
    grid_box_count = serializers.IntegerField(read_only=True)
    grid_boxes = GridBoxInPuckSerializer(source="cryogridbox_set", many=True, read_only=True)

    class Meta:
        model = Puck
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "cane_name",
            "position_in_cane",
            "max_boxes",
            "user_name",
            "grid_box_count",
            "grid_boxes",
        ]


class CaneSerializer(serializers.ModelSerializer):
    """
    Serializer for Cane model
    """

    color_code = serializers.CharField(source="get_color_display", read_only=True)
    pucks_count = serializers.SerializerMethodField()

    class Meta:
        model = Cane
        fields = [
            "id",
            "name",
            "color",
            "color_code",
            "position_in_dewar",
            "max_pucks",
            "dewar",
            "pucks_count",
        ]

    def get_pucks_count(self, obj):
        """Get count of pucks in this cane"""
        return obj.puck_set.count()


class PuckDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Puck with nested relationships
    """

    color_display = serializers.CharField(source="get_color_display", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    cane = CaneSerializer(source="cane", read_only=True)
    grid_boxes = CryoGridBoxSerializer(many=True, read_only=True)
    grid_boxes_count = serializers.SerializerMethodField()

    class Meta:
        model = Puck
        fields = [
            "id",
            "name",
            "color",
            "color_display",
            "position_in_cane",
            "max_boxes",
            "user_id",
            "user_name",
            "cane",
            "grid_boxes",
            "grid_boxes_count",
        ]

    def get_grid_boxes_count(self, obj):
        """Get count of grid boxes in this puck"""
        return obj.cryogridbox_set.count()


class GridDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing grid details
    """

    # Basic grid info - using SerializerMethodField to avoid source issues
    grid_name = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    notes = serializers.CharField(read_only=True)
    clipped = serializers.BooleanField(read_only=True)
    trashed = serializers.BooleanField(read_only=True)

    # Location info
    location = serializers.SerializerMethodField()

    # Related entities
    freezing_session = serializers.SerializerMethodField()
    specimen = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    position_in_box = serializers.IntegerField(read_only=True)
    copy_number = serializers.IntegerField(read_only=True)

    # Parameters
    parameters = serializers.SerializerMethodField()

    # Labels
    labels = serializers.SerializerMethodField()

    # Timestamps
    created_on = serializers.DateField(source="create_on", read_only=True)
    updated_on = serializers.DateField(read_only=True)

    class Meta:
        model = CryoGrid
        fields = [
            "id",
            "grid_name",
            "user",
            "notes",
            "clipped",
            "trashed",
            "location",
            "freezing_session",
            "specimen",
            "project",
            "position_in_box",
            "copy_number",
            "parameters",
            "labels",
            "created_on",
            "updated_on",
        ]

    def get_grid_name(self, obj):
        """Get grid name"""
        return obj.name

    def get_user(self, obj):
        """Get user username"""
        return obj.user.username if obj.user else None

    def get_location(self, obj):
        return {
            "puck_id": obj.grid_box.puck.id if obj.grid_box and obj.grid_box.puck else None,
            "puck_name": obj.grid_box.puck.name if obj.grid_box and obj.grid_box.puck else None,
            "puck_color": obj.grid_box.puck.color if obj.grid_box and obj.grid_box.puck else None,
            "grid_box_id": obj.grid_box.id if obj.grid_box else None,
            "grid_box_name": obj.grid_box.name if obj.grid_box else None,
            "position_in_box": obj.position_in_box,
            "position_in_puck": obj.grid_box.position_in_puck if obj.grid_box else None,
        }

    def get_freezing_session(self, obj):
        if obj.freezing_session:
            return {
                "id": obj.freezing_session.id,
                "name": f"{obj.freezing_session.datetime.date()}-{obj.freezing_session.user.username.split('@')[0] if obj.freezing_session.user else 'unknown'}-{obj.freezing_session.id}",
                "user": obj.freezing_session.user.username if obj.freezing_session.user else None,
                "device": obj.freezing_session.device.name if obj.freezing_session.device else None,
                "temperature": obj.freezing_session.device_temperature,
                "humidity": obj.freezing_session.humidity,
            }
        return None

    def get_specimen(self, obj):
        if obj.specimen:
            samples = []
            for sample in obj.specimen.samples.all():
                samples.append(
                    {
                        "id": sample.id,
                        "name": sample.name,
                        "ontology": sample.ontology,
                    }
                )
            return {
                "id": obj.specimen.id,
                "name": f"Specimen ({', '.join([s['name'] for s in samples])})" if samples else "Specimen (no samples)",
                "samples": samples,
                "notes": obj.specimen.notes,
            }
        return None

    def get_project(self, obj):
        if obj.intended_project:
            return {
                "id": obj.intended_project.id,
                "name": obj.intended_project.name,
                "description": getattr(obj.intended_project, "description", ""),
            }
        return None

    def get_parameters(self, obj):
        return {
            "blot_time": obj.blot_time,
            "blot_force": obj.blot_force,
            "blot_distance": obj.blot_distance,
        }

    def get_labels(self, obj):
        return [
            {
                "id": gl.label.id,
                "name": gl.label.name,
                "color": gl.label.color,
                "added_at": gl.added_at.isoformat() if gl.added_at else None,
                "added_by": gl.added_by.username if gl.added_by else None,
            }
            for gl in obj.gridlabel_set.select_related("label", "added_by").order_by("added_at")
        ]


class CryoGridSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating CryoGrid
    """

    grid_box_name = serializers.CharField(source="grid_box.name", read_only=True)

    class Meta:
        model = CryoGrid
        fields = [
            "id",
            "name",
            "user",
            "freezing_session",
            "specimen",
            "intended_project",
            "grid_box",
            "grid_box_name",
            "position_in_box",
            "notes",
            "clipped",
            "blot_time",
            "blot_force",
            "blot_distance",
            "copy_number",
            "trashed",
        ]
        read_only_fields = ["id", "trashed", "grid_box_name"]
        validators = []  # Disable default validators to use custom validation

    def validate(self, data):
        """
        Custom validation for grid creation/update
        """
        instance = self.instance

        # For updates, use existing values if not provided in data (partial update support)
        if instance:
            grid_box = data.get("grid_box", instance.grid_box)
            position_in_box = data.get("position_in_box", instance.position_in_box)
            name = data.get("name", instance.name)
            freezing_session = data.get("freezing_session", instance.freezing_session)
            specimen = data.get("specimen", instance.specimen)
            copy_number = data.get("copy_number", instance.copy_number)
        else:
            # For creation, get from data only
            grid_box = data.get("grid_box")
            position_in_box = data.get("position_in_box")
            name = data.get("name")
            freezing_session = data.get("freezing_session")
            specimen = data.get("specimen")
            copy_number = data.get("copy_number", 1)

        # Validate position is within grid box capacity
        if grid_box and position_in_box:
            if position_in_box > grid_box.max_grids:
                raise serializers.ValidationError(
                    {
                        "position_in_box": f"Position {position_in_box} exceeds maximum grids ({grid_box.max_grids}) for this box.",
                    }
                )

            # Check if position is already occupied
            position_query = CryoGrid.objects.filter(
                grid_box=grid_box,
                position_in_box=position_in_box,
                trashed=False,
            )
            if instance:
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                existing_grid = position_query.first()
                raise serializers.ValidationError(
                    {
                        "position_in_box": f'Position {position_in_box} is already occupied by grid "{existing_grid.name}".',
                    }
                )

        # Validate unique constraint on name, freezing_session, specimen, copy_number
        if name and specimen:
            unique_query = CryoGrid.objects.filter(
                name=name,
                freezing_session=freezing_session,
                specimen=specimen,
                copy_number=copy_number,
            )
            if instance:
                unique_query = unique_query.exclude(pk=instance.pk)
            if unique_query.exists():
                raise serializers.ValidationError(
                    {
                        "name": f'A grid with name "{name}", this specimen, freezing session, and copy number already exists.',
                    }
                )

        return data


class SampleSerializer(serializers.ModelSerializer):
    """
    Serializer for Sample model
    """

    class Meta:
        model = Sample
        fields = [
            "id",
            "name",
            "ontology",
        ]

    def validate_name(self, value):
        """Validate that sample name is unique and not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Sample name is required.")

        # Check for uniqueness
        instance = self.instance
        name_query = Sample.objects.filter(name=value.strip())
        if instance:
            name_query = name_query.exclude(pk=instance.pk)
        if name_query.exists():
            raise serializers.ValidationError(f'A sample with name "{value}" already exists.')

        return value.strip()

    def create(self, validated_data):
        """Create a new sample"""
        return Sample.objects.create(**validated_data)


class SpecimenSerializer(serializers.ModelSerializer):
    """
    Serializer for Specimen model with related samples
    """

    samples = SampleSerializer(many=True, read_only=True)
    sample_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="List of sample IDs to associate with this specimen",
    )
    documentation_page_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Specimen
        fields = [
            "id",
            "samples",
            "sample_ids",
            "notes",
            "documentation_page",
            "documentation_page_url",
            "display_name",
        ]

    def get_documentation_page_url(self, obj):
        """Get the URL of the documentation page if it exists"""
        if obj.documentation_page:
            return obj.documentation_page.url
        return None

    def get_display_name(self, obj):
        """Get human-readable display name"""
        return str(obj)

    def validate_sample_ids(self, value):
        """Validate that all sample IDs exist"""
        if value:
            existing_samples = Sample.objects.filter(id__in=value)
            if existing_samples.count() != len(value):
                existing_ids = set(existing_samples.values_list("id", flat=True))
                invalid_ids = set(value) - existing_ids
                raise serializers.ValidationError(
                    f"Sample IDs {invalid_ids} do not exist.",
                )
        return value

    def create(self, validated_data):
        """Create a new specimen with associated samples"""
        sample_ids = validated_data.pop("sample_ids", [])

        # Create the specimen
        specimen = Specimen.objects.create(
            notes=validated_data.get("notes", ""),
            documentation_page=validated_data.get("documentation_page", None),
        )

        # Associate samples if provided
        if sample_ids:
            samples = Sample.objects.filter(id__in=sample_ids)
            specimen.samples.set(samples)

        return specimen


class FreezingSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for PlungeFreezingSession model
    """

    user_name = serializers.CharField(source="user.username", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    display_name = serializers.SerializerMethodField()
    datetime = serializers.DateTimeField(required=False)

    class Meta:
        model = PlungeFreezingSession
        fields = [
            "id",
            "datetime",
            "user",
            "user_name",
            "device",
            "device_name",
            "device_temperature",
            "humidity",
            "documentation_page",
            "display_name",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.datetime:
            local_dt = django_timezone.localtime(instance.datetime)
            data["datetime"] = local_dt.isoformat()
        return data

    def get_display_name(self, obj):
        """Get human-readable display name matching the __str__ method"""
        return str(obj)


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for Project model
    """

    project_leader_name = serializers.SerializerMethodField(read_only=True)
    documentation_space_name = serializers.SerializerMethodField(read_only=True)
    documentation_space_url = serializers.SerializerMethodField(read_only=True)

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
