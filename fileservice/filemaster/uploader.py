"""
Routes used by the UDN Uploader Tool
"""
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from filemaster.aws import awsResource, awsBucketRegion, signedUrlUpload
from filemaster.models import ArchiveFile

LOGGER = logging.getLogger(__name__)


def is_bucket_valid(bucket):
    """
    Return True if we have the info configured to write to the bucket provided
    """
    try:
        return (
            hasattr(settings, 'BUCKET_CREDENTIALS') and
            settings.BUCKET_CREDENTIALS.get(bucket) and
            settings.BUCKET_CREDENTIALS[bucket].get('AWS_KEY_ID') and
            settings.BUCKET_CREDENTIALS[bucket].get('AWS_SECRET')) != None
    except Exception as exc:
        LOGGER.exception('Error thrown while looking up credentials for bucket %s: %s', bucket, exc)
        return False


def get_file_s3_data(location):
    """
    Return the S3 data for the location provided
    """
    try:
        bucket, path = location.get_bucket()
        region = awsBucketRegion(bucket)
        s3 = awsResource(service='s3', region=region)

        return s3.Object(bucket, path)
    except Exception as exc:
        LOGGER.exception(
            'Unable to fetch S3 data for file location %s with error: %s', location.id, exc)
        return None


def get_s3_upload_information(bucket, sequencing_file):
    """
    Plucks the needed values from the url hash
    """
    try:
        urlhash = signedUrlUpload(sequencing_file, bucket=bucket)

        access_key = urlhash['accesskey'] if 'accesskey' in urlhash else None
        folder_name = urlhash['foldername'] if 'foldername' in urlhash else None
        location_id = urlhash['locationid'] if 'locationid' in urlhash else None
        secret_key = urlhash['secretkey'] if 'secretkey' in urlhash else None
        session_token = urlhash['sessiontoken'] if 'sessiontoken' in urlhash else None

        return access_key, folder_name, location_id, secret_key, session_token
    except Exception as exc:
        LOGGER.exception(
            'Error thrown while attempting to get S3 upload info for file %s: %s', sequencing_file.filename, exc)
        return None, None, None, None, None


def mark_location_complete(file_size, location):
    """
    Update the location's filesize and uploadComplete attributes
    """
    try:
        location.filesize = file_size
        location.uploadComplete = datetime.now()
        location.save()

        return True
    except Exception as exc:
        LOGGER.exception(
            'Unable to update file location %s as complete with error: %s', location.id, exc)
        return False


class UploaderComplete(APIView):
    """
    API endpoint used by the UDN Uploader tool to mark a file upload as completed
    """

    def post(self, request):
        """
        Mark the file location, specified in the request as completed
        """
        try:
            location_id = request.data['location_id'] if 'location_id' in request.data else None
            uuid = request.data['uuid'] if 'uuid' in request.data else None

            if not location_id or not uuid:
                LOGGER.exception('Request to mark file complete missing required parameters')
                return Response(
                    {'error': 'Missing required parameters: location_id and uuid'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                sequencing_file = ArchiveFile.objects.get(uuid=uuid)
            except ArchiveFile.DoesNotExist:
                LOGGER.exception('Unable to find file %s to mark it as complete', uuid)
                return Response(
                    {'error': 'Unable to find requested sequencing file'}, status=status.HTTP_404_NOT_FOUND)

            try:
                location = sequencing_file.locations.get(id=location_id)
            except Exception:
                LOGGER.exception(
                    'Unable to find file location %s associated with file %s to mark it as complete',
                    location_id, uuid)
                return Response(
                    {'error': 'Mismatched location_id and uuid'}, status=status.HTTP_404_NOT_FOUND)

            if not location:
                LOGGER.exception(
                    'Unable to find file location %s associated with file %s to mark it as complete',
                    location_id, uuid)
                return Response(
                    {'error': 'Mismatched location_id and uuid'}, status=status.HTTP_404_NOT_FOUND)

            s3_data = get_file_s3_data(location)
            file_size = s3_data.content_length if s3_data and s3_data.content_length else None

            if not file_size:
                LOGGER.exception(
                    'Unable to get file_size from S3 data for location %s to mark it as complete', location_id)
                return Response(
                    {'error': 'Unable to get S3 data for file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            updated = mark_location_complete(file_size, location)

            if not updated:
                LOGGER.exception(
                    'Unable to mark file location %s as complete', location_id)
                return Response(
                    {'error': 'Unable to update FileService location as complete'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            location.refresh_from_db()

            return Response({
                'description': sequencing_file.description,
                'filesize': location.filesize,
                'upload_completed': location.uploadComplete,
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            LOGGER.exception(
                'Unknown error while attempting to mark file location %s as complete: %s', location_id, exc)
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


class UploaderNew(APIView):
    """
    API endpoint used by the UDN Uploader tool to create a new file entry
    """

    def post(self, request):
        """
        Create a new ArchiveFile record with the data provided
        """
        try:
            bucket = request.data['bucket'] if 'bucket' in request.data else None
            description = request.data['description'] if 'description' in request.data else None
            filename = request.data['filename'] if 'filename' in request.data else None
            metadata = request.data['metadata'] if 'metadata' in request.data else None
            permissions = request.data['permissions'] if 'permissions' in request.data else None
            user_email = request.data['user_email'] if 'user_email' in request.data else None

            if not bucket or not description or not filename or not metadata or not permissions or not user_email:
                LOGGER.exception('Request to upload new file missing required parameters')
                return Response(
                    {'error': 'Missing required parameters: bucket, description, filename, metadata, permissions, user_email'},
                    status=status.HTTP_400_BAD_REQUEST)

            if not is_bucket_valid(bucket):
                return Response({'error': 'Provided bucket is not a valid upload location'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                User = get_user_model()
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                LOGGER.exception('Unable to find user by email specified')
                return Response({'error': 'Unable to find user by email specified'}, status=status.HTTP_403_FORBIDDEN)

            try:
                sequencing_file = ArchiveFile.objects.create(
                    description=description, filename=filename, metadata=metadata, owner=user)
            except Exception as exc:
                LOGGER.exception('Exception thrown while attempting to create a new file with name %s: %s', filename, exc)
                return Response(
                    {'error': 'Error thrown while attempting to create file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                for perm in permissions:
                    sequencing_file.setPerms(perm)
            except Exception as exc:
                LOGGER.exception(
                    'Exception thrown while attempting to set permissions on a new file with name %s: %s', filename, exc)
                return Response(
                    {'error': 'Exception thrown while attempting to create file'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            (access_key, folder_name, location_id, secret_key,
             session_token) = get_s3_upload_information(bucket, sequencing_file)

            return Response({
                'access_key': access_key,
                'folder_name': folder_name,
                'location_id': location_id,
                'secret_key': secret_key,
                'session_token': session_token,
                'uuid': sequencing_file.uuid,
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            LOGGER.exception(
                'Exception thrown while attempting to create new file with name: %s', exc)
            return Response(
                {'error': 'Unknown error while attempting to create new file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploaderUpdate(APIView):
    """
    API endpoint used by the UDN Uploader tool to add a new location to an
    existing file entry
    """

    def post(self, request):
        """
        Create a new ArchiveFile record with the data provided
        """
        try:
            bucket = request.data['bucket'] if 'bucket' in request.data else None
            uuid = request.data['uuid'] if 'uuid' in request.data else None

            if not bucket or not uuid:
                LOGGER.exception('Request to add location to existing file is missing required fields')
                return Response(
                    {'error': 'Missing required parameters: bucket and uuid'},
                    status=status.HTTP_400_BAD_REQUEST)

            if not is_bucket_valid(bucket):
                return Response({'error': 'Provided bucket is not a valid upload location'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                sequencing_file = ArchiveFile.objects.get(uuid=uuid)
            except ArchiveFile.DoesNotExist:
                LOGGER.exception('Unable to find file %s to add a new location', uuid)
                return Response(
                    {'error': 'Unable to find requested sequencing file'}, status=status.HTTP_404_NOT_FOUND)

            (access_key, folder_name, location_id, secret_key,
             session_token) = get_s3_upload_information(bucket, sequencing_file)

            return Response({
                'access_key': access_key,
                'folder_name': folder_name,
                'location_id': location_id,
                'secret_key': secret_key,
                'session_token': session_token,
                'uuid': sequencing_file.uuid,
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            LOGGER.exception(
                'Error thrown while attempting to add a new location to the file %s: %s', uuid, exc)
            return Response(
                {'error': 'Unknown error while attempting to create new file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
