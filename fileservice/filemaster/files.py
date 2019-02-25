import sys
from urllib.parse import urlparse
import urllib
from uuid import uuid4
from datetime import datetime

import boto3
from boto.s3.connection import S3Connection
from botocore.client import Config
from rest_framework.decorators import detail_route, list_route
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from django_filters import rest_framework as rest_framework_filters
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from filemaster.models import ArchiveFile, FileLocation, Bucket
from filemaster.serializers import ArchiveFileSerializer
from filemaster.permissions import DjangoObjectPermissionsAll
from filemaster.filters import ArchiveFileFilter
from filemaster.aws import signedUrlUpload, signedUrlDownload

import logging
log = logging.getLogger(__name__)

# Get the current user model
User = get_user_model()


# TODO: Replace DetailRoutes here with the newer DRF whatever
class ArchiveFileList(viewsets.ModelViewSet):
    queryset = ArchiveFile.objects.all()
    serializer_class = ArchiveFileSerializer
    lookup_field = 'uuid'
    filter_class = ArchiveFileFilter
    filter_backends = (rest_framework_filters.DjangoFilterBackend, filters.DjangoObjectPermissionsFilter,)

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
        if uuids_string is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Break them apart.
        uuids = uuids_string.split(',')
        if len(uuids) == 0:
            return HttpResponseBadRequest()

        try:
            # Fetch the files
            archivefiles = ArchiveFile.objects.filter(uuid__in=uuids)
        except:
            return HttpResponseNotFound()

        # Filter out files the user doesn't have permissions for
        archivefiles_allowed = [archivefile for archivefile in archivefiles
                                if request.user.has_perm('filemaster.view_archivefile', archivefile)]

        # Check for an empty set and quit early.
        if len(archivefiles_allowed) == 0:
            return HttpResponseForbidden()

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
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.delete_archivefile', archivefile):
            return HttpResponseForbidden()

        fl = FileLocation.objects.get(id=location)
        bucket, path = fl.get_bucket()
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)
        if not aws_key:
            aws_key = settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID")
        if not aws_secret:
            aws_secret = settings.BUCKETS.get(bucket, {}).get('AWS_SECRET')

        conn = S3Connection(aws_key, aws_secret, is_secure=True)
        b = conn.get_bucket(bucket)
        k = b.get_key(path)

        # Delete it.
        if k is not None:
            k.delete()

        # Remove everything.
        fl.delete()
        archivefile.delete()

        return Response({'message': "file deleted", "uuid": uuid})

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def download(self, request, uuid=None):
        url = None
        archivefile = None
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.download_archivefile', archivefile):
            return HttpResponseForbidden()
        # get presigned url
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)

        url = signedUrlDownload(archivefile, aws_key=aws_key, aws_secret=aws_secret)
        return Response({'url': url})

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
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
        bucket = self.request.query_params.get('bucket', settings.S3_DEFAULT_BUCKET)

        # Generate a folder name
        folder_name = str(uuid4())
        log.debug('Folder: {}'.format(folder_name))

        # Ensure the bucket is writable
        if not request.user.has_perm('filemaster.write_bucket', Bucket.objects.get(name=bucket)):
            return HttpResponseForbidden()

        # Build the key
        key = folder_name + "/" + archive_file.filename
        log.debug('Key: {}'.format(key))

        # Get credentials
        aws_key = self.request.query_params.get('aws_key', settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID"))
        aws_secret = self.request.query_params.get('aws_secret', settings.BUCKETS.get(bucket, {}).get('AWS_SECRET'))

        # Generate the post
        s3 = boto3.client('s3',
                          aws_access_key_id=aws_key,
                          aws_secret_access_key=aws_secret,
                          config=Config(signature_version='s3v4'))

        post = s3.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            ExpiresIn=expires,
        )

        # Form the URL to the file
        url = "S3://%s/%s" % (bucket, key)
        log.debug('Url: {}'.format(url))

        # Register file
        file_location = FileLocation(url=url, storagetype=settings.BUCKETS[bucket]['type'])
        file_location.save()
        archive_file.locations.add(file_location)

        # Return the POST to the uploader
        return Response({'post': post,
                         'locationid': file_location.id})

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def upload(self, request, uuid=None):
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

        cloud = self.request.query_params.get('cloud', "aws")
        bucket = self.request.query_params.get('bucket', settings.S3_DEFAULT_BUCKET)
        sys.stderr.write("bucket %s\n" % bucket)
        bucketobj = Bucket.objects.get(name=bucket)
        if not request.user.has_perm('filemaster.write_bucket', bucketobj):
            return HttpResponseForbidden()

        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)

        urlhash = signedUrlUpload(archivefile, bucket=bucket, aws_key=aws_key, aws_secret=aws_secret, cloud=cloud)

        url = urlhash["url"]
        message = "PUT to this url"
        location = urlhash["location"]
        locationid = urlhash["locationid"]

        # get presigned url
        return Response({'url': url,
                         'message': message,
                         'location': location,
                         'locationid': locationid,
                         'bucket': urlhash['bucket'],
                         'foldername': urlhash['foldername'],
                         'filename': urlhash['filename'],
                         'secretkey': urlhash['secretkey'],
                         'accesskey': urlhash['accesskey'],
                         'sessiontoken': urlhash['sessiontoken']})

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def uploadcomplete(self, request, uuid=None):
        from datetime import datetime
        archivefile = None
        message = None

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
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)
        if not aws_key:
            aws_key = settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID")
        if not aws_secret:
            aws_secret = settings.BUCKETS.get(bucket, {}).get('AWS_SECRET')

        conn = S3Connection(aws_key, aws_secret, is_secure=True)
        b = conn.get_bucket(bucket)
        k = b.get_key(path)
        fl.filesize = k.size
        fl.uploadComplete = datetime.now()
        fl.save()
        return Response({'message': "upload complete", "filename": archivefile.filename, "uuid": archivefile.uuid})

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
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
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)
        if not aws_key:
            aws_key = settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID")
        if not aws_secret:
            aws_secret = settings.BUCKETS.get(bucket, {}).get('AWS_SECRET')

        conn = S3Connection(aws_key, aws_secret, is_secure=True)
        b = conn.get_bucket(bucket)
        k = b.get_key(path)

        # Check for etag
        if not k.etag or len(k.etag) < 2:
            log.error('ETag is missing or invalid: {}'.format(k.etag))
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Return etag, stripping quotes
        return Response(k.etag[1:-1])

    @detail_route(methods=['post'], permission_classes=[DjangoObjectPermissionsAll])
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

    @list_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
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
            archivefiles = ArchiveFile.objects.filter(uuid__in=uuids)
        except:
            return HttpResponseNotFound()

        # Filter out files the user doesn't have permissions for
        archivefiles_allowed = [archivefile for archivefile in archivefiles
                                if request.user.has_perm('filemaster.view_archivefile', archivefile)]

        # Check for an empty set and quit early.
        if len(archivefiles_allowed) == 0:
            return HttpResponseForbidden()

        # Set credentials
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)

        # get presigned urls and prepare response body
        body = ''
        for archivefile in archivefiles_allowed:

            # Get tje location
            location = archivefile.locations.first()

            # Get the URL
            url = signedUrlDownload(archivefile, aws_key=aws_key, aws_secret=aws_secret)

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

    @detail_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def proxy(self, request, uuid=None):
        url = None
        archivefile = None
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()

        if not request.user.has_perm('filemaster.download_archivefile', archivefile):
            return HttpResponseForbidden()
        # get presigned url
        aws_key = self.request.query_params.get('aws_key', None)
        aws_secret = self.request.query_params.get('aws_secret', None)

        url = signedUrlDownload(archivefile, aws_key=aws_key, aws_secret=aws_secret)

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
