from rest_framework import serializers
from django.contrib.auth.models import User
from cryo_grids.models import Puck, CryoGridBox, Cane, CryoGrid
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
            'cane'
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
                    'name': f'A puck with name "CZII-0{name}" and color "{color_display}" already exists.'
                })
             
        # Validate unique cane+position
        if cane and position_in_cane:
            position_query = Puck.objects.filter(cane=cane, position_in_cane=position_in_cane)
            if instance:
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError({
                    'position_in_cane': f'Position {position_in_cane} in this cane is already occupied.'
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
            'puck_user'
        ]

    def validate(self, data):
        """
        Custom validation for grid box creation/update
        """
        name = data.get('name')
        puck = data.get('puck')
        position_in_puck = data.get('position_in_puck')
            
        instance = self.instance
            
        if name:
            name_query = CryoGridBox.objects.filter(name=name)
            if instance:  # If updating, exclude current instance
                name_query = name_query.exclude(pk=instance.pk)
            if name_query.exists():
                raise serializers.ValidationError({
                    'name': f'A grid box with name "{name}" already exists.'
                })
            
        if puck and position_in_puck:
            position_query = CryoGridBox.objects.filter(
                puck=puck, 
                position_in_puck=position_in_puck
            )
            if instance:  # If updating, exclude current instance
                position_query = position_query.exclude(pk=instance.pk)
            if position_query.exists():
                raise serializers.ValidationError({
                    'position_in_puck': f'Position {position_in_puck} in this puck is already occupied.'
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
            'pucks_count'
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
            'position_in_box', 'copy_number', 'parameters'
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
            "position_in_box": obj.position_in_box
        }
    
    def get_freezing_session(self, obj):
        if obj.freezing_session:
            return {
                "id": obj.freezing_session.id,
                "name": f"{obj.freezing_session.datetime.date()}-{obj.freezing_session.user.username.split('@')[0] if obj.freezing_session.user else 'unknown'}-{obj.freezing_session.id}",
                "user": obj.freezing_session.user.username if obj.freezing_session.user else None,
                "device": obj.freezing_session.device.name if obj.freezing_session.device else None,
                "temperature": obj.freezing_session.device_temperature,
                "humidity": obj.freezing_session.humidity
            }
        return None
    
    def get_specimen(self, obj):
        if obj.specimen:
            samples = []
            for sample in obj.specimen.samples.all():
                samples.append({
                    "id": sample.id,
                    "name": sample.name,
                    "ontology": sample.ontology
                })
            return {
                "id": obj.specimen.id,
                "name": f"Specimen ({', '.join([s['name'] for s in samples])})" if samples else "Specimen (no samples)",
                "samples": samples,
                "notes": obj.specimen.notes
            }
        return None
    
    def get_project(self, obj):
        if obj.intended_project:
            return {
                "id": obj.intended_project.id,
                "name": obj.intended_project.name,
                "description": getattr(obj.intended_project, 'description', '')
            }
        return None
    
    def get_parameters(self, obj):
        return {
            "blot_time": obj.blot_time,
            "blot_force": obj.blot_force,
            "blot_distance": obj.blot_distance
        }
   