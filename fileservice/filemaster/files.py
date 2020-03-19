import logging
import base64
import json
import urllib

from botocore.exceptions import ClientError
from datetime import datetime
from uuid import uuid4
from urllib.parse import urlparse

from rest_framework.decorators import action
from rest_framework import status
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response

from django_filters import rest_framework as rest_framework_filters
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter
from guardian.shortcuts import get_objects_for_user

from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http import HttpResponseServerError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from filemaster.aws import awsCopyFile
from filemaster.aws import awsMoveFile
from filemaster.aws import awsRemoveFile
from filemaster.aws import signedUrlDownload
from filemaster.aws import awsClient, awsResource
from filemaster.filters import ArchiveFileFilter
from filemaster.models import ArchiveFile
from filemaster.models import Bucket
from filemaster.models import DownloadLog
from filemaster.models import FileLocation
from filemaster.serializers import ArchiveFileSerializer
from filemaster.serializers import DownloadLogSerializer
from filemaster.permissions import DjangoObjectPermissionsAll

log = logging.getLogger(__name__)

# Get the current user model
User = get_user_model()


class ArchiveFileList(viewsets.ModelViewSet):
    queryset = ArchiveFile.objects.all()
    serializer_class = ArchiveFileSerializer
    lookup_field = 'uuid'
    filter_class = ArchiveFileFilter
    filter_backends = (rest_framework_filters.DjangoFilterBackend, DjangoObjectPermissionsFilter,)

    def perform_create(self, serializer):
        log.debug("[files][ArchiveFileList][pre_savepre_save] - Making user owner.")
        user = User.objects.get(email=self.request.user.email)
        obj = serializer.save(owner=user)

        # Check request
        removeTags = self.request.query_params.get('removeTags', None)
        removePerms = self.request.query_params.get('removePerms', None)

        if removeTags:
            try:
                af = ArchiveFile.objects.get(uuid=obj.uuid)
                af.tags.clear()
            except Exception as e:
                log.error("ERROR tags: %s " % e)

        if removePerms:
            try:
                af = ArchiveFile.objects.get(uuid=obj.uuid)
                af.killPerms()
            except:
                pass

        if 'permissions' in self.request.data:
            for p in self.request.data['permissions']:
                try:
                    af = ArchiveFile.objects.get(uuid=obj.uuid)
                    af.setPerms(p)
                except Exception as e:
                    log.error("ERROR permissions: %s " % e)

    def retrieve(self, request, *args, **kwargs):
        log.debug("[files][ArchiveFileList][list] - Retrieving File: {}".format(kwargs.get('uuid')))

        # Get the UUIDs from the request data.
        uuid = kwargs.get('uuid')
        if uuid is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the files
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        # Check for an empty set and quit early.
        if not request.user.has_perm('filemaster.view_archivefile', archivefile):
            return HttpResponseForbidden()

        # Serialize them.
        serializer = ArchiveFileSerializer(archivefile, many=False)

        # Return them
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        log.debug("[files][ArchiveFileList][list] - Listing Files.")

        # Get the UUIDs from the request data.
        uuids_string = self.request.query_params.get('uuids', None)
        if uuids_string:
            log.debug(f'Finding files for UUIDs: {uuids_string}')

            # Break them apart.
            uuids = uuids_string.split(',')
            if len(uuids) == 0:
                return HttpResponseBadRequest()

            try:
                # Fetch the files
                archivefiles = ArchiveFile.objects.filter(uuid__in=uuids)
            except:
                return HttpResponseNotFound()

        else:
            log.debug(f'Finding files for user: {request.user.username}')

            # Get all files for the requesting user
            try:
                # Fetch the files
                archivefiles = ArchiveFile.objects.filter(owner=request.user.id)
            except:
                return HttpResponseNotFound()

        # Filter out files the user doesn't have permissions for
        archivefiles_allowed = [archivefile for archivefile in archivefiles
                                if request.user.has_perm('filemaster.view_archivefile', archivefile)]

        # Check for an empty set and quit early.
        if len(archivefiles_allowed) == 0:
            return HttpResponseForbidden()

        # Check for bucket filter
        bucket = request.query_params.get('bucket')
        if bucket:
            log.debug(f'Filtering files in S3 bucket: {bucket}')

            # Iterate locations
            archivefiles_allowed = [file for file in archivefiles if bucket in
                                    [fl.get_bucket()[0] for fl in file.locations.all()]]

        # Serialize them.
        serializer = ArchiveFileSerializer(archivefiles_allowed, many=True)

        # Return them
        return Response(serializer.data)

    def destroy(self, request, uuid=None, *args, **kwargs):

        # UUID is required.
        if not uuid:
            return HttpResponseBadRequest('"uuid" is required')

        # Get the location from the query
        location = self.request.query_params.get('location', None)
        if not location:
            return HttpResponseBadRequest('"location" parameter is required')

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)

            # Fetch the file location
            fl = FileLocation.objects.get(id=location)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.delete_archivefile', archivefile):
            return HttpResponseForbidden()

        try:
            # Delete it.
            log.debug(f'Deleting S3 file: {fl.url}')
            if awsRemoveFile(fl):

                # Remove everything.
                log.debug(f'Deleting file location: {fl.id}')
                fl.delete()

                # If file has no remaining locations, delete it as well
                if archivefile.locations.count() == 0:
                    log.debug(f'ArchiveFile {archivefile.uuid} has no locations, deleting entirely')

                    # Delete the file
                    archivefile.delete()

                    return Response({'message': "file deleted", "uuid": uuid})

                else:
                    log.debug(f'ArchiveFile {archivefile.uuid} has remaining locations, will not delete')

                    return Response({'message': "file location deleted", "uuid": uuid, "location": fl.url})

        except Exception as e:
            log.exception(f'File delete error: {e}', exc_info=True, extra={
                'file': archivefile.uuid, 'location': fl.url
            })

        return Response({'message': "file not deleted", "uuid": uuid}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[DjangoObjectPermissionsAll])
    def copy(self, request, uuid):

        # Get bucket
        destination = request.query_params.get('to')
        origin = request.query_params.get('from')

        # Ensure it exists
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)

            # Get the location
            if not origin:
                origin, path = next(archivefile.locations).get_bucket()
                log.debug(f'Origin not provided, using "{origin}"')
        except:
            return HttpResponseNotFound()

        # Check request
        if not uuid or not destination or not origin:
            return HttpResponseBadRequest('File UUID, origin and destination bucket are required')

        try:
            # Check bucket perms
            if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=origin)):
                return HttpResponseForbidden(f'User does not have permissions on Bucket "{origin}"')
        except Bucket.DoesNotExist:
            return HttpResponseNotFound(f'Bucket "{origin}" does not exist in Fileservice')

        try:
            # Check bucket perms
            if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=destination)):
                return HttpResponseForbidden(f'User does not have permissions on Bucket "{destination}"')
        except Bucket.DoesNotExist:
            return HttpResponseNotFound(f'Bucket "{destination}" does not exist in Fileservice')

        # Check permissions on file
        if not request.user.has_perm('filemaster.change_archivefile', archivefile):
            return HttpResponseForbidden(f'User does not have \'change\' permission on \'{uuid}\'')

        # Get location
        location = archivefile.get_location(origin)
        if not location:
            return HttpResponseBadRequest(f'File {uuid} has multiple locations, \'from\' must be specified')

        try:
            # Perform the copy
            new_location = awsCopyFile(archivefile, destination, origin)
            if not new_location:
                log.error(f'Could not copy file {archivefile.uuid}')
                return HttpResponseServerError(f'Could not copy file {archivefile.uuid}')

            return Response({'message': 'copied', 'url': new_location.url, 'uuid': uuid})

        except Exception as e:
            log.exception('File move error: {}'.format(e), exc_info=True, extra={
                'archivefile': archivefile.id, 'uuid': uuid, 'location': location.id,
                'origin': origin, 'destination': destination,
            })

            return HttpResponseServerError('Error copying file')

    @action(detail=True, methods=['post'], permission_classes=[DjangoObjectPermissionsAll])
    def move(self, request, uuid):

        # Get bucket
        destination = request.query_params.get('to')
        origin = request.query_params.get('from')

        # Ensure it exists
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)

            # Get the location
            if not origin and archivefile.locations.first():
                origin, path = archivefile.locations.first().get_bucket()
                log.debug(f'Origin not provided, using "{origin}"')
        except ArchiveFile.DoesNotExist:
            return HttpResponseNotFound(f'ArchiveFile \'{uuid}\' could not be found')

        except Exception as e:
            log.exception(f'Move error: {e}', exc_info=True, extra={
                'request': request, 'uuid': uuid,
            })
            return HttpResponseNotFound(f'Location for ArchiveFile \'{uuid}\' could not be found')

        # Check request
        if not uuid or not destination or not origin:
            return HttpResponseBadRequest('File UUID, "from" and "to" bucket are required')

        try:
            # Check bucket perms
            if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=origin)):
                return HttpResponseForbidden(f'User does not have permissions on Bucket "{origin}"')
        except Bucket.DoesNotExist:
            return HttpResponseNotFound(f'Bucket "{origin}" does not exist in Fileservice')

        try:
            # Check bucket perms
            if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=destination)):
                return HttpResponseForbidden(f'User does not have permissions on Bucket "{destination}"')
        except Bucket.DoesNotExist:
            return HttpResponseNotFound(f'Bucket "{destination}" does not exist in Fileservice')

        # Check permissions on file
        if not request.user.has_perm('filemaster.change_archivefile', archivefile):
            return HttpResponseForbidden(f'User does not have \'change\' permission on \'{uuid}\'')

        # Get location
        location = archivefile.get_location(origin)
        if not location:
            return HttpResponseBadRequest(f'File {uuid} has multiple locations, \'from\' must be specified')

        try:
            # Perform the copy
            new_location = awsMoveFile(archivefile, destination, origin)
            if not new_location:
                log.error(f'Could not move file {archivefile.uuid}')
                return HttpResponseServerError(f'Could not move file {archivefile.uuid}')

            return Response({'message': 'moved', 'url': new_location.url, 'uuid': uuid})

        except Exception as e:
            log.exception('File move error: {}'.format(e), exc_info=True, extra={
                'archivefile': archivefile.id, 'uuid': uuid, 'location': location.id,
                'origin': origin, 'destination': destination
            })

            return HttpResponseServerError('Error moving file')

    @action(detail=True, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def download(self, request, uuid=None):

        # Get the file record
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.download_archivefile', archivefile):
            return HttpResponseForbidden()

        # Get presigned url
        url = signedUrlDownload(archivefile)

        # Save a download log
        DownloadLog.objects.create(archivefile=archivefile, requesting_user=request.user)

        return Response({'url': url})

    @action(detail=True, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def post(self, request, uuid=None):

        # Get the file record
        try:
            archive_file = ArchiveFile.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        # Check permissions
        if not request.user.has_perm('filemaster.upload_archivefile', archive_file):
            return HttpResponseForbidden()

        # Pull request parameters
        expires = int(self.request.query_params.get('expires', '10'))
        bucket = self.request.query_params.get('bucket')

        # If no bucket specified, default to first created
        if not bucket:
            try:
                bucket = next(settings.BUCKETS)
            except Exception as e:
                log.exception(f'Error finding default bucket: {e}', exc_info=True, extra={'request': request})
                return HttpResponseBadRequest(f'No default bucket has been configured for Fileservice, must specify'
                                              f'bucket in request')

        try:
            # Check bucket perms
            if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=bucket)):
                return HttpResponseForbidden(f'User does not have permissions on Bucket "{bucket}"')
        except Bucket.DoesNotExist:
            return HttpResponseNotFound(f'Bucket "{bucket}" does not exist in Fileservice')

        # Check for extra conditions
        conditions = []
        try:
            conditions_b64 = self.request.query_params.get('conditions')
            if conditions_b64:

                # Decode and load
                conditions = json.loads(base64.b64decode(conditions_b64.encode()).decode())

                log.debug('Extra conditions: {}'.format(conditions))

        except Exception as e:
            log.exception('Conditions error: {}'.format(e), exc_info=True, extra={
                'conditions': self.request.query_params.get('conditions'),
            })

        # Generate a folder name
        folder_name = str(uuid4())

        # Ensure the bucket is writable
        if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=bucket)):
            return HttpResponseForbidden()

        # Build the key
        key = folder_name + "/" + archive_file.filename

        # Generate the post
        s3 = awsClient(service='s3')

        post = s3.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            ExpiresIn=expires,
            Conditions=conditions,
        )

        # Form the URL to the file
        url = "S3://%s/%s" % (bucket, key)
        log.debug('Url: {}'.format(url))

        # Register file
        file_location = FileLocation(url=url, storagetype='s3')
        file_location.save()
        archive_file.locations.add(file_location)

        # Return the POST to the uploader
        return Response({'post': post,
                         'locationid': file_location.id})

    @action(detail=True, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def uploadcomplete(self, request, uuid=None):

        # Get location
        location = self.request.query_params.get('location', None)

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)

            # Check for missing location.
            if not location and archivefile.locations.first():
                location = archivefile.locations.first().id
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.upload_archivefile', archivefile):
            return HttpResponseForbidden()

        if not location:
            return HttpResponseForbidden()

        fl = FileLocation.objects.get(id=location)
        bucket, path = fl.get_bucket()

        try:
            # Get the object if it exists
            s3 = awsResource(service='s3')
            k = s3.Object(bucket, path)
            fl.filesize = k.content_length
            fl.uploadComplete = datetime.now()
            fl.save()

            return Response({'message': "upload complete", "filename": archivefile.filename, "uuid": archivefile.uuid})
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return HttpResponseBadRequest()
            else:
                log.exception(f'Boto Error: {e}', exc_info=True, extra={'uuid': uuid, 'location': location})
                return HttpResponseServerError()
        except Exception as e:
            log.exception(f'Fileservice Error: {e}', exc_info=True, extra={'uuid': uuid, 'location': location})
            return HttpResponseServerError()

    @action(detail=True, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def filehash(self, request, uuid=None):

        # Get location
        location = self.request.query_params.get('location', None)

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)

            # Check for missing location.
            if not location and archivefile.locations.first():
                location = archivefile.locations.first().id
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.upload_archivefile', archivefile):
            return HttpResponseForbidden()

        if not location:
            return HttpResponseForbidden()

        fl = FileLocation.objects.get(id=location)
        bucket, path = fl.get_bucket()

        try:
            # Get the object if it exists
            s3 = awsResource(service='s3')
            k = s3.Object(bucket, path)

            return Response(k.e_tag)

        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return HttpResponseBadRequest()
            else:
                log.exception(f'Boto Error: {e}', exc_info=True, extra={'uuid': uuid, 'location': location})
                return HttpResponseServerError()

        except Exception as e:
            log.exception(f'Fileservice Error: {e}', exc_info=True, extra={'uuid': uuid, 'location': location})
            return HttpResponseServerError()

    @action(detail=True, methods=['post'], permission_classes=[DjangoObjectPermissionsAll])
    def register(self, request, uuid=None):
        log.debug("[files][ArchiveFileList][register] - Registering file.")
        # take uuid, create presigned url, put location into original file
        archivefile = None
        message = None
        url = None

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.upload_archivefile', archivefile):
            return HttpResponseForbidden()

        if 'location' in self.request.data:
            if self.request.data['location'].startswith("file://"):
                fl = FileLocation(url=self.request.data['location'])
                fl.save()
                archivefile.locations.add(fl)
                url = self.request.data['location']
                message = "Local location %s added to file %s" % (self.request.data['location'], archivefile.uuid)
            elif self.request.data['location'].startswith("S3://"):
                fl = None
                try:
                    # if file already exists, see if user has upload rights
                    fl = FileLocation.objects.get(url=self.request.data['location'])
                    for af in ArchiveFile.objects.filter(locations__id=fl.pk):
                        if not request.user.has_perm('filemaster.upload_archivefile', af):
                            return HttpResponseForbidden()
                    archivefile.locations.add(fl)
                    message = "S3 location %s added to file %s" % (self.request.data['location'], archivefile.uuid)
                except:
                    # if file doesn't exist, register it.
                    fl = FileLocation(url=self.request.data['location'])
                    fl.save()
                    archivefile.locations.add(fl)
                    message = "S3 location %s added to file %s" % (self.request.data['location'], archivefile.uuid)
            else:
                return HttpResponseBadRequest("Currently only 'file://' and 'S3://' accepted at this time.")

        # get presigned url
        return Response({'message': message})

    @action(detail=False, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def archive(self, request):
        log.debug("[files][ArchiveFileList][archive] - Archiving Files: {}".format(request.query_params.get('uuids')))

        # Get the UUIDs from the request data.
        uuids_string = self.request.query_params.get('uuids', None)
        if uuids_string is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Break them apart.
        uuids = uuids_string.split(',')
        if len(uuids) == 0:
            return HttpResponseBadRequest()

        try:
            # Fetch the files
            archivefiles = ArchiveFile.objects.filter(uuid__in=uuids, deletedate__isnull=True, locations__isnull=False)
        except:
            return HttpResponseNotFound()

        # Filter out files the user doesn't have permissions for
        archivefiles_allowed = [archivefile for archivefile in archivefiles
                                if request.user.has_perm('filemaster.view_archivefile', archivefile)]

        # Check for an empty set and quit early.
        if len(archivefiles_allowed) == 0:
            return HttpResponseForbidden(f'User does not have "view_archivefile" permission on requested files')

        # get presigned urls and prepare response body
        body = ''
        for archivefile in archivefiles_allowed:

            # Get tje location
            location = archivefile.locations.first()

            # Get the URL
            url = signedUrlDownload(archivefile)

            # Prepare the parts
            protocol = urlparse(url).scheme
            path = urllib.parse.quote_plus(url.replace(protocol + '://', ''))

            # Build the remote proxy URL
            proxy_url = '/proxy/' + protocol + '/' + path

            # Add the entry
            body += f'- {location.filesize} {proxy_url} {archivefile.filename}\n'

        # Forward it on
        log.debug('Archive request: \n\n{}\n\n'.format(body))

        # Check for specified filename
        if request.query_params.get('filename'):
            archive_filename = request.query_params.get('filename')
        else:
            # Set the name of the output
            archive_filename = f'archive.{datetime.now().isoformat().replace(":", "")}.zip'

        # Let NGINX handle it
        response = HttpResponse(body)
        response['X-Archive-Files'] = 'zip'
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(archive_filename)

        log.debug(f'Sending user to archive proxy: {response}')

        return response

    @action(detail=True, methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def proxy(self, request, uuid=None):

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.download_archivefile', archivefile):
            return HttpResponseForbidden()

        # Generate pre-signed URL
        url = signedUrlDownload(archivefile)

        # Save a download log
        DownloadLog.objects.create(archivefile=archivefile, requesting_user=request.user)

        # Prepare the parts
        protocol = urlparse(url).scheme

        # Get the remainder
        path = url.replace(protocol + '://', '')

        # Let NGINX handle it
        response = HttpResponse()
        response['X-Accel-Redirect'] = '/proxy/' + protocol + '/' + urllib.parse.quote_plus(path)

        # Set the filename and ensure it is URL encoded
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(archivefile.filename)

        log.debug(f'Sending user to S3 proxy: {response["X-Accel-Redirect"]}')

        return response


class DownloadLogList(generics.ListAPIView):
    """
    A read-only endpoint for retreiving download logs.
    """

    serializer_class = DownloadLogSerializer

    def get_queryset(self):

        # Get all the archivefiles that the user has access to.
        archivefiles = get_objects_for_user(self.request.user, 'filemaster.view_archivefile')

        # Then establish a queryset of DownloadLogs relevant only to those archivefiles.
        queryset = DownloadLog.objects.filter(archivefile__in=archivefiles)

        user_email = self.request.query_params.get('user_email', None)
        if user_email is not None:
            queryset = queryset.filter(requesting_user__email=user_email)

        uuid = self.request.query_params.get('uuid', None)
        if uuid is not None:
            queryset = queryset.filter(archivefile__uuid=uuid)

        filename = self.request.query_params.get('filename', None)
        if filename is not None:
            queryset = queryset.filter(archivefile__filename=filename)

        download_date_gte = self.request.query_params.get('download_date_gte', None)
        if download_date_gte is not None:
            queryset = queryset.filter(download_requested_on__gte=download_date_gte)

        download_date_lte = self.request.query_params.get('download_date_lte', None)
        if download_date_lte is not None:
            queryset = queryset.filter(download_requested_on__lte=download_date_lte)

        return queryset
