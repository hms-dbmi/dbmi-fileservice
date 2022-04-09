"""
Routes used by the UDN Uploader Tool
"""
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from filemaster.models import ArchiveFile, FileLocation

LOGGER = logging.getLogger(__name__)


class UploaderComplete(APIView):
    """
    API endpoint used by the UDN Uploader tool to add an uploaded file to FS
    """

    def post(self, request):
        """
        Mark the file location, specified in the request as completed
        """
        try:
            required_fields = [
                'description', 'filename', 'filesize', 'metadata', 'permissions', 'storage_location',
                'storage_type', 'user_email', 'uuid']
            for field in required_fields:
                if field not in request.data:
                    LOGGER.exception('Request to upload new file missing required parameters')
                    return Response(
                        {'error': 'Missing required parameters: {}'.format(', '.join(required_fields))},
                        status=status.HTTP_400_BAD_REQUEST)
            
            try:
                User = get_user_model()
                user = User.objects.get(email=request.data['user_email'])
            except User.DoesNotExist:
                LOGGER.exception('Unable to find user by email specified')
                return Response({'error': 'Unable to find user by email specified'}, status=status.HTTP_403_FORBIDDEN)

            try:
                sequencing_file = ArchiveFile.objects.get(uuid=request.data['uuid'])
                sequencing_file.description=request.data['description']
                sequencing_file.metadata=request.data['metadata']
                sequencing_file.save()
            except ArchiveFile.DoesNotExist:
                sequencing_file = ArchiveFile.objects.create(
                    description=request.data['description'], filename=request.data['filename'],
                    metadata=request.data['metadata'], owner=user, uuid=request.data['uuid'])

            try:
                sequencing_file.killPerms()

                for perm in request.data['permissions']:
                    sequencing_file.setPerms(perm)
            except Exception as exc:
                LOGGER.exception(
                    'Exception thrown while attempting to set permissions on a new file with name %s: %s', request.data['filename'], exc)
                return Response(
                    {'error': 'Exception thrown while attempting to create file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            location = FileLocation(
                filesize=request.data['filesize'], storagetype=request.data['storage_type'],
                uploadComplete=datetime.now(), url=request.data['storage_location'])
            location.save()
            sequencing_file.locations.add(location)

            return Response({
                'location_id': location.id,
                'uuid': sequencing_file.uuid,
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            LOGGER.exception(
                'Unknown error while attempting to mark file location %s as complete: %s', location.id, exc)
            return Response(
                {'error': 'Unknown error while attempting to mark file complete'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploaderCheck(APIView):
    """
    API endpoint used by the UDN Uploader tool to check that FileService is up
    """

    def get(self, _):
        """
        Check that the services is up and can get files
        """
        try:
            ArchiveFile.objects.first()

            return Response('FileService up and running', status=status.HTTP_200_OK)
        except Exception as exc:
            LOGGER.exception('Healthcheck failed with error: %s' % exc)
            return Response(
                'FileService unable to respond correctly at this time', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploaderMetadata(APIView):
    """
    API endpoint used by the UDN Uploader tool to update an existing file's metadata
    """

    def put(self, request):
        """
        Update the metadata of an existing file
        """
        try:
            description = request.data['description'] if 'description' in request.data else None
            filename = request.data['filename'] if 'filename' in request.data else None
            metadata = request.data['metadata'] if 'metadata' in request.data else None

            if not description or not filename or not metadata:
                LOGGER.exception('Request to update metadata missing required parameters')
                return Response(
                    {'error': 'Missing required parameters: description, filename, metadata'},
                    status=status.HTTP_400_BAD_REQUEST)

            try:
                sequencing_file = ArchiveFile.objects.get(filename=filename)
            except ArchiveFile.DoesNotExist:
                LOGGER.exception('Unable to find file with name %s to update metadata', filename)
                return Response(
                    {'error': 'Unable to find file to update'}, status=status.HTTP_404_NOT_FOUND)

            try:
                sequencing_file.description = description
                sequencing_file.metadata = metadata
                sequencing_file.save()
            except Exception as exc:
                LOGGER.exception('Exception thrown while updating metadata for file with name %s: %s', filename, exc)
                return Response(
                    {'error': 'Exception thrown while updating metadata for file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({'message': 'Metadata successfully updated'}, status=status.HTTP_200_OK)
        except Exception as exc:
            LOGGER.exception(
                'Exception thrown while attempting to update metadata for file with name: %s', exc)
            return Response(
                {'error': 'Unknown error while attempting to update file metadata'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
