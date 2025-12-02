from cryo_grids.models import Cane, CryoGrid, CryoGridBox, Puck, Specimen, Sample, PlungeFreezingSession
from django.contrib.auth.models import User
from rest_framework import serializers
from confluence.models import Page, Space
from clouddocs.models import DriveFolder
from projects.models import Project

from umbrella.choices import PUCK_COLORS


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    full_name = serializers.SerializerMethodField()
    clean_username = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'clean_username',
            'first_name',
            'last_name',
            'full_name',
            'email',
        ]
    
    def get_full_name(self, obj):
        """Get full name or username if no name is provided"""
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name if full_name else obj.username
    
    def get_clean_username(self, obj):
        """Remove domain part from username if present"""
        username = obj.username
        if '@' in username:
            return username.split('@')[0]
        return username

class PuckSerializer(serializers.ModelSerializer):
    """
    Serializer for Puck model with essential fields
    """
    color_display = serializers.CharField(source='get_color_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Puck
        fields = [
            'id',
            'name',
            'color',
            'color_display',
            'position_in_cane',
            'max_boxes',
            'user',
            'user_name',
            'cane',
        ]
        validators = []

    def validate(self, data):
        """
        Custom validation for puck creation/update
        """
        # Check for unique name + color combination
        name = data.get('name')
        color = data.get('color')
        cane = data.get('cane')
        position_in_cane = data.get('position_in_cane')

        # Get instance for update operations
        instance = self.instance

        # Validate unique name+color
        if name and color:
            puck_query = Puck.objects.filter(name=name, color=color)
            print(puck_query)
            if instance:
                puck_query = puck_query.exclude(pk=instance.pk)
            if puck_query.exists():
                color_display = dict(PUCK_COLORS).get(color, color)
                raise serializers.ValidationError({
                    'name': f'A puck with name "CZII-0{name}" and color "{color_display}" already exists.',
                })

        # Validate unique cane+position
        if cane and position_in_cane:
            position_query = Puck.objects.filter(cane=cane, position_in_cane=position_in_cane)
            if instance:
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError({
                    'position_in_cane': f'Position {position_in_cane} in this cane is already occupied.',
                })

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
    color_display = serializers.CharField(source='get_color_display', read_only=True)
    numbering_display = serializers.CharField(source='get_numbering_display', read_only=True)
    puck_user = serializers.CharField(source='puck.user.username', read_only=True)

    class Meta:
        model = CryoGridBox
        fields = [
            'id',
            'name',
            'color',
            'color_display',
            'numbering',
            'numbering_display',
            'position_in_puck',
            'max_grids',
            'puck',
            'puck_user',
        ]
        validators = [] #disables default validators
        extra_kwargs = {
            'name': {'validators': []},  # to disable unique validator on name field
        }

    def validate(self, data):
        """
        Custom validation for grid box creation/update
        """
        name = data.get('name')
        puck = data.get('puck')
        position_in_puck = data.get('position_in_puck')

        instance = self.instance

        if name:
            name_query = CryoGridBox.objects.filter( puck=puck,
            position_in_puck=position_in_puck,
            name=name)
            if instance:  # If updating, exclude current instance
                name_query = name_query.exclude(pk=instance.pk)
            if name_query.exists():
                raise serializers.ValidationError({
                    'name': f'A grid box with name "{name}" at position {position_in_puck} in this puck already exists.',
                })

        if puck and position_in_puck:
            position_query = CryoGridBox.objects.filter(
                puck=puck,
                position_in_puck=position_in_puck,
            )
            if instance:  # If updating, exclude current instance
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError({
                    'position_in_puck': f'Position {position_in_puck} in this puck is already occupied.',
                })

        return data

class CryoGridSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating CryoGrid
    """
    grid_box_name = serializers.CharField(source='grid_box.name', read_only=True)
    
    class Meta:
        model = CryoGrid
        fields = [
            'id',
            'name',
            'user',
            'freezing_session',
            'specimen',
            'intended_project',
            'grid_box',
            'grid_box_name',
            'position_in_box',
            'notes',
            'clipped',
            'blot_time',
            'blot_force',
            'blot_distance',
            'copy_number',
            'trashed',
        ]
        read_only_fields = ['id', 'trashed', 'grid_box_name']
        validators = []  # Disable default validators to use custom validation
        
    def validate(self, data):
        """
        Custom validation for grid creation/update
        """
        instance = self.instance
        
        # For updates, use existing values if not provided in data (partial update support)
        if instance:
            grid_box = data.get('grid_box', instance.grid_box)
            position_in_box = data.get('position_in_box', instance.position_in_box)
            name = data.get('name', instance.name)
            freezing_session = data.get('freezing_session', instance.freezing_session)
            specimen = data.get('specimen', instance.specimen)
            copy_number = data.get('copy_number', instance.copy_number)
        else:
            # For creation, get from data only
            grid_box = data.get('grid_box')
            position_in_box = data.get('position_in_box')
            name = data.get('name')
            freezing_session = data.get('freezing_session')
            specimen = data.get('specimen')
            copy_number = data.get('copy_number', 1)
        
        
        # Validate position is within grid box capacity
        if grid_box and position_in_box:
            if position_in_box > grid_box.max_grids:
                raise serializers.ValidationError({
                    'position_in_box': f'Position {position_in_box} exceeds maximum grids ({grid_box.max_grids}) for this box.',
                })
            
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
                raise serializers.ValidationError({
                    'position_in_box': f'Position {position_in_box} is already occupied by grid "{existing_grid.name}".',
                })
        
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
                raise serializers.ValidationError({
                    'name': f'A grid with name "{name}", this specimen, freezing session, and copy number already exists.',
                })
        
        return data

class CaneSerializer(serializers.ModelSerializer):
    """
    Serializer for Cane model
    """
    color_code = serializers.CharField(source='get_color_display', read_only=True)
    pucks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cane
        fields = [
            'id',
            'name',
            'color',
            'color_code',
            'position_in_dewar',
            'max_pucks',
            'dewar',
            'pucks_count',
        ]
    
    def get_pucks_count(self, obj):
        """Get count of pucks in this cane"""
        return obj.puck_set.count()
        
class PuckDetailSerializer(serializers.ModelSerializer):
    color_display = serializers.CharField(source='get_color_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    cane = CaneSerializer(source='cane', read_only=True)
    grid_boxes = CryoGridBoxSerializer(many=True, read_only=True)
    grid_boxes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Puck
        fields = [
            'id',
            'name',
            'color',
            'color_display',
            'position_in_cane',
            'max_boxes',
            'user_id',
            'user_name',
            'cane',
            'grid_boxes',
            'grid_boxes_count',
        ]

        def get_grid_boxes_count(self, obj):
            """Get count of grid boxes in this puck"""
            return obj.cryogridbox_set.count()

class GridDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing grid details - matches your UI form
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
    
    class Meta:
        model = CryoGrid
        fields = [
            'grid_name', 'user', 'notes', 'clipped', 'trashed',
            'location', 'freezing_session', 'specimen', 'project',
            'position_in_box', 'copy_number', 'parameters',
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
            "grid_box_id": obj.grid_box.id if obj.grid_box else None,
            "grid_box_name": obj.grid_box.name if obj.grid_box else None,
            "position_in_box": obj.position_in_box,
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
                samples.append({
                    "id": sample.id,
                    "name": sample.name,
                    "ontology": sample.ontology,
                })
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
                "description": getattr(obj.intended_project, 'description', ''),
            }
        return None
    
    def get_parameters(self, obj):
        return {
            "blot_time": obj.blot_time,
            "blot_force": obj.blot_force,
            "blot_distance": obj.blot_distance,
        }

class SampleSerializer(serializers.ModelSerializer):
    """
    Serializer for Sample model
    """
    class Meta:
        model = Sample
        fields = [
            'id',
            'name',
            'ontology',
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
        help_text="List of sample IDs to associate with this specimen"
    )
    notes_page_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Specimen
        fields = [
            'id',
            'samples',
            'sample_ids',
            'notes',
            'notes_page',
            'notes_page_url',
            'display_name',
        ]
    
    def get_notes_page_url(self, obj):
        """Get the URL of the notes page if it exists"""
        if obj.notes_page:
            return obj.notes_page.url if hasattr(obj.notes_page, 'url') else None
        return None
    
    def get_display_name(self, obj):
        """Get human-readable display name"""
        return str(obj)
    
    def validate_sample_ids(self, value):
        """Validate that all sample IDs exist"""
        if value:
            existing_samples = Sample.objects.filter(id__in=value)
            if existing_samples.count() != len(value):
                existing_ids = set(existing_samples.values_list('id', flat=True))
                invalid_ids = set(value) - existing_ids
                raise serializers.ValidationError(
                    f"Sample IDs {invalid_ids} do not exist."
                )
        return value
    
    def create(self, validated_data):
        """Create a new specimen with associated samples"""
        sample_ids = validated_data.pop('sample_ids', [])
        
        # Create the specimen
        specimen = Specimen.objects.create(
            notes=validated_data.get('notes', ''),
            notes_page=validated_data.get('notes_page', None)
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
    user_name = serializers.CharField(source='user.username', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PlungeFreezingSession
        fields = [
            'id',
            'datetime',
            'user',
            'user_name',
            'device',
            'device_name',
            'device_temperature',
            'humidity',
            'notes_page',
            'display_name',
        ]
    
    def get_display_name(self, obj):
        """Get human-readable display name matching the __str__ method"""
        return str(obj)

class ConfluenceSpaceSerializer(serializers.ModelSerializer):
    """Serializer for Confluence Space model"""
    class Meta:
        model = Space
        fields = ['id', 'name', 'space_id', 'url']

class DriveFolderSerializer(serializers.ModelSerializer):
    """Serializer for Google Drive Folder model"""
    class Meta:
        model = DriveFolder
        fields = ['id', 'name', 'url']

class ConfluencePageSerializer(serializers.ModelSerializer):
    """Serializer for Confluence Page model (for notes pages)"""
    class Meta:
        model = Page
        fields = ['id', 'name', 'url']

class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""

    project_leader_name = serializers.SerializerMethodField(read_only=True)
    confluence_space_name = serializers.CharField(source='confluence_space.space_id', read_only=True)
    google_drive_folder_name = serializers.CharField(source='google_drive_folder.name', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'project_leader',
            'project_leader_name',
            'confluence_space',
            'confluence_space_name',
            'google_drive_folder',
            'google_drive_folder_name',
        ]
        read_only_fields = ['id']

    def get_project_leader_name(self, obj):
        """Get project leader's username"""
        if obj.project_leader:
            return obj.project_leader.username
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
        According to the model, only name is truly required (not null and unique)
        Other fields can be null/blank based on the model definition
        """
        
        # Validate foreign keys exist if provided
        if 'project_leader' in data and data['project_leader'] is not None:
            if not User.objects.filter(id=data['project_leader'].id).exists():
                raise serializers.ValidationError({
                    'project_leader': 'Selected user does not exist.'
                })
        
        if 'confluence_space' in data and data['confluence_space'] is not None:
            if not Space.objects.filter(id=data['confluence_space'].id).exists():
                raise serializers.ValidationError({
                    'confluence_space': 'Selected confluence space does not exist.'
                })
        
        if 'google_drive_folder' in data and data['google_drive_folder'] is not None:
            if not DriveFolder.objects.filter(id=data['google_drive_folder'].id).exists():
                raise serializers.ValidationError({
                    'google_drive_folder': 'Selected Google Drive folder does not exist.'
                })
        
        return data