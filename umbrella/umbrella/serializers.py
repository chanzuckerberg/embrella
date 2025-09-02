from rest_framework import serializers
from django.contrib.auth.models import User


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
