from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from rest_framework.authtoken.models import Token
from drf_compound_fields.fields import ListField,DictField,ListOrItemField
from rest_framework import relations

from .models import HealthCheck,ArchiveFile,FileLocation

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')

class FileLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileLocation
        fields = ('id', 'url')


class UserSerializer(serializers.Serializer):
    email = serializers.CharField(required=False)

    class Meta:
        fields = ('email',)

class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        
class SpecialGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    users = UserSerializer(required=False)

    class Meta:
        fields = ('id','name','users')    
       
class HealthCheckSerializer(serializers.ModelSerializer):
    message = serializers.CharField()    
    
    class Meta:
        model = HealthCheck
        fields = ('id', 'message')

class JSONFieldSerializer(serializers.WritableField):
    def to_native(self, obj):
        return obj
        
class ArchiveFileSerializer(serializers.ModelSerializer):
    tags = serializers.Field(source='get_tags_display')
    metadata = JSONFieldSerializer(required=False)
    owner = UserSerializer(required=False)
    locations = FileLocationSerializer(required=False)
    class Meta:
        model = ArchiveFile
        lookup_field = 'uuid'
        fields = ('id','uuid','description','metadata','tags','owner','filename','locations')
