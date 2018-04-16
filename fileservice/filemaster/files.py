from rest_framework.decorators import detail_route, list_route
from rest_framework import status,filters,viewsets,mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.http import Http404,HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseBadRequest,HttpResponseForbidden, HttpResponseServerError, HttpResponse,HttpResponseNotFound, HttpResponseRedirect
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from .models import ArchiveFile, FileLocation, Bucket

from django.contrib.auth.models import User, Group, Permission

from .serializers import ArchiveFileSerializer

from .authenticate import Auth0Authentication, ServiceAuthentication

from .permissions import DjangoObjectPermissionsAll,DjangoObjectPermissionsChange
from .filters import ArchiveFileFilter

from .aws import signedUrlUpload, signedUrlDownload

from boto.s3.connection import S3Connection

import sys
from uuid import uuid4
import boto3
from botocore.client import Config

import logging
log = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
User = get_user_model()

class ArchiveFileList(viewsets.ModelViewSet):
    queryset = ArchiveFile.objects.all()
    serializer_class = ArchiveFileSerializer
    lookup_field = 'uuid'
    authentication_classes = (Auth0Authentication, TokenAuthentication, ServiceAuthentication,)
    permission_classes = (IsAuthenticated, DjangoObjectPermissionsChange,)
    filter_class = ArchiveFileFilter
    filter_backends = (filters.DjangoFilterBackend, filters.DjangoObjectPermissionsFilter,)

    def pre_save(self, obj):
        log.debug("[files][ArchiveFileList][pre_savepre_save] - Making user owner.")
        u = User.objects.get(email=self.request.user.email)
        obj.owner = u

    def post_save(self, obj, created=False):
        removeTags = self.request.QUERY_PARAMS.get('removeTags', None)
        removePerms = self.request.QUERY_PARAMS.get('removePerms', None)
        tagstash = []
        if removeTags:
            try:
                af = ArchiveFile.objects.get(uuid=obj.uuid)
                af.tags.clear()
            except Exception, e:
                print "ERROR tags: %s " % e
        if 'tags' in self.request.DATA:
            for t in self.request.DATA['tags']:
                tagstash.append(t)
            map(obj.tags.add, tagstash)

        if removePerms:
            try:
                af = ArchiveFile.objects.get(uuid=obj.uuid)
                af.killPerms()
            except:
                pass
        if 'permissions' in self.request.DATA:
            for p in self.request.DATA['permissions']:
                try:
                    af = ArchiveFile.objects.get(uuid=obj.uuid)
                    af.setPerms(p)
                except Exception, e:
                    print "ERROR permissions: %s " % e
        return super(ArchiveFileList, self).post_save(obj)

    @list_route(methods=['get'], permission_classes=[DjangoObjectPermissionsAll])
    def list(self, request, *args, **kwargs):
        log.debug("[files][ArchiveFileList][list] - Listing Files.")
        # Get the UUIDs from the request data.
        uuids_string = self.request.QUERY_PARAMS.get('uuids', None)
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
        location = self.request.QUERY_PARAMS.get('location', None)
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
        aws_key = self.request.QUERY_PARAMS.get('aws_key', None)
        aws_secret = self.request.QUERY_PARAMS.get('aws_secret', None)
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
        aws_key = self.request.QUERY_PARAMS.get('aws_key', None)
        aws_secret = self.request.QUERY_PARAMS.get('aws_secret', None)

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
        expires = int(self.request.QUERY_PARAMS.get('expires', '10'))
        bucket = self.request.QUERY_PARAMS.get('bucket', settings.S3_UPLOAD_BUCKET)

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
        aws_key = self.request.QUERY_PARAMS.get('aws_key', settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID"))
        aws_secret = self.request.QUERY_PARAMS.get('aws_secret', settings.BUCKETS.get(bucket, {}).get('AWS_SECRET'))

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

        cloud = self.request.QUERY_PARAMS.get('cloud', "aws")
        bucket = self.request.QUERY_PARAMS.get('bucket', settings.S3_UPLOAD_BUCKET)
        sys.stderr.write("bucket %s\n" % bucket)
        bucketobj = Bucket.objects.get(name=bucket)
        if not request.user.has_perm('filemaster.write_bucket', bucketobj):
            return HttpResponseForbidden()

        aws_key = self.request.QUERY_PARAMS.get('aws_key', None)
        aws_secret = self.request.QUERY_PARAMS.get('aws_secret', None)

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
        location = self.request.QUERY_PARAMS.get('location', None)

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
        aws_key = self.request.QUERY_PARAMS.get('aws_key', None)
        aws_secret = self.request.QUERY_PARAMS.get('aws_secret', None)
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

        if 'location' in self.request.DATA:
            if self.request.DATA['location'].startswith("file://"):
                fl = FileLocation(url=self.request.DATA['location'])
                fl.save()
                archivefile.locations.add(fl)
                url = self.request.DATA['location']
                message = "Local location %s added to file %s" % (self.request.DATA['location'], archivefile.uuid)
            elif self.request.DATA['location'].startswith("S3://"):
                fl = None
                try:
                    # if file already exists, see if user has upload rights
                    fl = FileLocation.objects.get(url=self.request.DATA['location'])
                    for af in ArchiveFile.objects.filter(locations__id=fl.pk):
                        if not request.user.has_perm('filemaster.upload_archivefile', af):
                            return HttpResponseForbidden()
                    archivefile.locations.add(fl)
                    message = "S3 location %s added to file %s" % (self.request.DATA['location'], archivefile.uuid)
                except:
                    # if file doesn't exist, register it.
                    fl = FileLocation(url=self.request.DATA['location'])
                    fl.save()
                    archivefile.locations.add(fl)
                    message = "S3 location %s added to file %s" % (self.request.DATA['location'], archivefile.uuid)
            else:
                return HttpResponseBadRequest("Currently only 'file://' and 'S3://' accepted at this time.")

        # get presigned url
        return Response({'message': message})