from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from rest_framework.authtoken.models import Token
from drf_compound_fields.fields import ListField,DictField,ListOrItemField

from .models import HealthCheck

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email')
        
class SpecialGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    users = ListOrItemField(DictField(required=False),required=False)

    class Meta:
        fields = ('id','name','users')    
       
class HealthCheckSerializer(serializers.ModelSerializer):
    message = serializers.CharField()    
    
    class Meta:
        model = HealthCheck
        fields = ('id', 'message')
        
