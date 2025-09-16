from rest_framework import serializers
from django.contrib.auth.models import User
from cryo_grids.models import Puck, CryoGridBox, Cane, CryoGrid


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
            'user_id',
            'user_name',
            'cane'
        ]
class CryoGridBoxSerializer(serializers.ModelSerializer):
    """
    Serializer for CryoGridBox model
    """
    color_display = serializers.CharField(source='get_color_display', read_only=True)
    numbering_display = serializers.CharField(source='get_numbering_display', read_only=True)
    
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
            'puck'
        ]
    

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
   