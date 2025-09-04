from rest_framework import serializers
from django.contrib.auth.models import User
from cryo_grids.models import Puck, CryoGridBox, Cane


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