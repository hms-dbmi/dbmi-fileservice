import json
import ast

from rest_framework import serializers
from rest_framework.authtoken.models import Token

from taggit_serializer.serializers import TagListSerializerField
from taggit_serializer.serializers import TaggitSerializer

from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from .models import ArchiveFile
from .models import CustomUser
from .models import DownloadLog
from .models import FileLocation
from .models import FileOperation

class WritableField(serializers.Field):
    def to_representation(self, value):
        return self.to_native(value)

    def to_internal_value(self, data):
        return self.to_native(data)

    def to_native(self, data):
        """
        Transform the *incoming* primitive data into a native value.
        """
        raise NotImplementedError(
            '{cls}.to_internal_value() must be implemented.'.format(
                cls=self.__class__.__name__
            )
        )


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class FileLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileLocation
        fields = ('id', 'url', 'uploadComplete', 'storagetype', 'filesize')


class TokenSerializer(serializers.ModelSerializer):
    token = serializers.ReadOnlyField(source='key')
    class Meta:
        model = Token
        fields = ('token',)


class UserSerializer(serializers.Serializer):
    email = serializers.CharField(required=False)

    class Meta:
        fields = ('email',)


class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = User


class BucketSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)

    class Meta:
        fields = ('name',)


class SpecialGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    users = UserSerializer(required=False, many=True)
    buckets = BucketSerializer(required=False, many=True)

    class Meta:
        fields = ('id', 'name', 'users', 'buckets',)


class JSONFieldSerializer(WritableField):
    def to_native(self, obj):
        return obj


class ArchiveFileSimpleSerializer(TaggitSerializer, serializers.ModelSerializer):
    permissions = serializers.ListField(read_only=True, source='get_permissions_display')
    tags = TagListSerializerField(required=False)
    metadata = JSONFieldSerializer(required=False)
    permissions = serializers.ListField(read_only=True, source='get_permissions_display')
    expirationdate = serializers.DateField(required=False)

    class Meta:
        model = ArchiveFile
        fields = ('id', 'uuid', 'description', 'metadata', 'tags', 'owner', 'filename',
        'locations', 'permissions', 'creationdate', 'modifydate', 'expirationdate')


class ArchiveFileSerializer(ArchiveFileSimpleSerializer):
    owner = UserSerializer(required=False)
    locations = serializers.SerializerMethodField('get_locations_list')

    class Meta:
        model = ArchiveFile
        lookup_field = 'uuid'
        fields = ('id', 'uuid', 'description', 'metadata', 'tags', 'owner', 'filename',
        'locations', 'permissions', 'creationdate', 'modifydate', 'expirationdate')

    def get_locations_list(self, instance):
        locations = instance.locations.all().order_by('id')
        return FileLocationSerializer(locations, many=True, context=self.context).data


class JSONSearchField(WritableField):

    def to_native(self, value):
        con_value = ast.literal_eval(value)
        return json.dumps(con_value)


class TagSearchField(WritableField):
    def to_native(self, value):
        return value


class SearchSerializer(TaggitSerializer, serializers.Serializer):
    #text = serializers.CharField()
    #creationdate = serializers.DateTimeField(source="creationdate")
    #modifydate = serializers.DateTimeField(source="modifydate")
    description = serializers.CharField(source="description")
    filename = serializers.CharField(source="filename")
    uuid = serializers.CharField(source="uuid")
    owner = serializers.CharField(source="owner")
    tags = TagListSerializerField()
    #metadata = MetadataSearchSerializer(source='metadata')
    metadata = JSONSearchField(source='metadata')


class DownloadLogArchiveFileSerializer(serializers.ModelSerializer):
    """
    This serializer hides some ArchiveFile fields that are not needed in DownloadLog results.
    """

    class Meta:
        model = ArchiveFile
        lookup_field = 'uuid'
        fields = ('id', 'uuid', 'description', 'owner', 'filename', 'creationdate')


class DownloadLogRequestingUserSerializer(serializers.ModelSerializer):
    """
    This serializer only needs to return the user's email address.
    """

    class Meta:
        model = CustomUser
        fields = ('email', )


class DownloadLogSerializer(serializers.ModelSerializer):
    requesting_user = DownloadLogRequestingUserSerializer()
    archivefile = DownloadLogArchiveFileSerializer()

    class Meta:
        model = DownloadLog
        fields = ('archivefile', 'download_requested_on', 'requesting_user')
        depth = 1


class FileOperationSerializer(serializers.ModelSerializer):
    archivefile = ArchiveFileSimpleSerializer()
    origin_location = FileLocationSerializer()
    destination_location = FileLocationSerializer()

    class Meta:
        model = FileOperation
        fields = (
            'uuid', 'archivefile', 'creationdate',
            'modifydate', 'operation', 'completiondate',
            'origin', 'destination', 'succeeded',
            'origin_location', 'destination_location'
        )
