"""
API Endpoint used by the Gateway to manage Realigned Files
"""
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from filemaster.models import ArchiveFile, FileLocation

LOGGER = logging.getLogger(__name__)


class CreateRealignedFile(APIView):
    """
    API Endpoint used by the Gateway to manage Realigned Files
    """

    def post(self, request):
        """
        Create entries for a new realigned file
        """
        try:
            bucket = request.data['bucket'] if 'bucket' in request.data else None
            description = request.data['description'] if 'description' in request.data else None
            filename = request.data['filename'] if 'filename' in request.data else None
            filesize = request.data['filesize'] if 'filesize' in request.data else None
            folder = request.data['folder'] if 'folder' in request.data else None
            metadata = request.data['metadata'] if 'metadata' in request.data else None
            permissions = request.data['permissions'] if 'permissions' in request.data else None
            storagetype = request.data['storagetype'] if 'storagetype' in request.data else None
            user_email = request.data['user_email'] if 'user_email' in request.data else None

            if not all([bucket, description, filename, filesize, folder, metadata, storagetype, user_email]):
                return Response({'error': 'Missing required data'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                User = get_user_model()
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                LOGGER.exception('Unable to find user by email specified')
                return Response({'error': 'Unable to find user by email specified'}, status=status.HTTP_403_FORBIDDEN)

            new_file = ArchiveFile.objects.create(
                description=description, filename=filename, metadata=metadata, owner=user)

            location = FileLocation(
                filesize=filesize, storagetype=storagetype, uploadComplete=datetime.now(), url=''.format())
            new_file.locations.add(location)

            try:
                for perm in permissions:
                    new_file.setPerms(perm)
            except Exception as exc:
                LOGGER.exception(
                    'Exception thrown while attempting to set permissions on a new file with name %s: %s', filename, exc)
                return Response(
                    {'error': 'Exception thrown while attempting to create file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'location_id': location.id,
                'uuid': new_file.uuid,
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            LOGGER.exception(
                'Unknown error while attempting to create a new realigned file entry: %s', exc)
            return Response(
                {'error': 'Unknown error while attempting to create a new realigned file entry'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
