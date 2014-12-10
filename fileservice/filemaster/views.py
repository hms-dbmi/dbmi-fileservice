from django.shortcuts import render
from django.db import models
from django.http import Http404,HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseBadRequest,HttpResponseForbidden, HttpResponseServerError, HttpResponse,HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import logout,authenticate, login
from django.contrib.sites.models import Site
from django.core.files.storage import default_storage

from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib.admin.sites import site
from django.template import RequestContext, loader

from rest_framework import status,filters,viewsets,mixins
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import detail_route, list_route
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


from .models import HealthCheck,GROUPTYPES,ArchiveFile,FileLocation
from .authenticate import ExampleAuthentication,Auth0Authentication
from .serializers import HealthCheckSerializer,UserSerializer,GroupSerializer,SpecialGroupSerializer,ArchiveFileSerializer,TokenSerializer, SearchSerializer
from .permissions import DjangoObjectPermissionsAll,DjangoModelPermissionsAll,DjangoObjectPermissionsChange
from rest_framework_extensions.mixins import DetailSerializerMixin
from guardian.shortcuts import assign_perm
from django.contrib.auth import get_user_model
import json,uuid
from boto.s3.connection import S3Connection
from haystack.forms import ModelSearchForm
from haystack.query import EmptySearchQuerySet,SearchQuerySet,SQ


User = get_user_model()        

class HealthCheckList(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('message', 'id')

class ArchiveFileList(viewsets.ModelViewSet):
    queryset = ArchiveFile.objects.all()
    serializer_class = ArchiveFileSerializer
    lookup_field = 'uuid'    
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,DjangoObjectPermissionsChange,)
    filter_backends = (filters.DjangoFilterBackend,filters.DjangoObjectPermissionsFilter,)
    filter_fields = ('uuid',)

    def pre_save(self, obj):
        u = User.objects.get(email=self.request.user.email)
        obj.owner = u
        

    def post_save(self, obj, created=False):
        #if 'tags' in self.request.DATA:
        #    self.object.tags.set(*self.request.DATA['tags']) # type(self.object.tags) == <taggit.managers._TaggableManager>
        removeTags = self.request.QUERY_PARAMS.get('removeTags', None)
        removePerms = self.request.QUERY_PARAMS.get('removePerms', None)
        tagstash=[]        
        if removeTags and 'tags' in self.request.DATA:
            try:
                af = ArchiveFile.objects.get(uuid=obj.uuid)
                af.tags.clear()                
            except Exception,e:
                print "ERROR tags: %s " % e
        if 'tags' in self.request.DATA:        
            for t in self.request.DATA['tags']:
                tagstash.append(t)
            map(obj.tags.add, tagstash)

        if removePerms and 'permissions' in self.request.DATA:
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
                except Exception,e:
                    print "ERROR permissions: %s " % e
        return super(ArchiveFileList, self).post_save(obj)        

    @detail_route(methods=['get'])
    def download(self, request, uuid=None):
        url = None
        archivefile=None
        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()
        
        if not request.user.has_perm('filemaster.download_archivefile',archivefile):
            return HttpResponseForbidden()
        #get presigned url
        url = signedUrlDownload(archivefile)
        return Response({'url': url})

    @detail_route(methods=['get'])
    def upload(self, request, uuid=None):
        #take uuid, create presigned url, put location into original file
        archivefile=None
        message=None
        url = None

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()
        
        if not request.user.has_perm('filemaster.upload_archivefile',archivefile):
            return HttpResponseForbidden()
        
        bucket = self.request.QUERY_PARAMS.get('bucket', None)
        
        urlhash = signedUrlUpload(archivefile,bucket=bucket)
        url = urlhash["url"]
        message = "PUT to this url"
        location = urlhash["location"]
            
        #get presigned url
        return Response({'url': url,'message':message,'location':location})

    @detail_route(methods=['post'])
    def register(self, request, uuid=None):
        #take uuid, create presigned url, put location into original file
        archivefile=None
        message=None
        url = None

        try:
            archivefile = ArchiveFile.objects.get(uuid=uuid)
        except:
            return HttpResponseNotFound()
        
        if not request.user.has_perm('filemaster.upload_archivefile',archivefile):
            return HttpResponseForbidden()
        
        if 'location' in self.request.DATA:
            if self.request.DATA['location'].startswith("file://"):
                fl = FileLocation(url=self.request.DATA['location'])
                fl.save()
                archivefile.locations.add(fl)
                url = self.request.DATA['location']
                message="Local location %s added to file %s" % (self.request.DATA['location'],archivefile.uuid)
            elif self.request.DATA['location'].startswith("S3://"):
                fl = None
                try:
                    fl = FileLocation.objects.get(url=self.request.DATA['location'])
                    for af in ArchiveFile.objects.filter(locations__id=fl.pk):
                        if not request.user.has_perm('filemaster.upload_archivefile',af):
                            return HttpResponseForbidden()
                    archivefile.locations.add(fl)
                    message = "S3 location %s added to file %s" % (self.request.DATA['location'],archivefile.uuid)
                except:
                    fl = FileLocation(url=self.request.DATA['location'])
                    fl.save()
                    archivefile.locations.add(fl)
                    message="S3 location %s added to file %s" % (self.request.DATA['location'],archivefile.uuid)
            else:
                return HttpResponseBadRequest("Currently only 'file://' and 'S3://' accepted at this time.")
                
                                
        #get presigned url
        return Response({'message':message})


def signedUrlUpload(archiveFile=None,bucket=None):
    conn = S3Connection(settings.S3_ID, settings.S3_SECRET, is_secure=True)
    foldername = str(uuid.uuid4())
    if not bucket:
        bucket=settings.S3_UPLOAD_BUCKET

    url = "S3://%s/%s" % (bucket,foldername+"/"+archiveFile.filename)
    fl = FileLocation(url=url)
    fl.save()
    archiveFile.locations.add(fl)
    return {
            "url":conn.generate_url(3600*24, 'PUT', bucket, foldername+"/"+archiveFile.filename),
            "location":"s3://"+bucket+"/"+foldername+"/"+archiveFile.filename
            }

def signedUrlDownload(archiveFile=None):
    conn = S3Connection(settings.S3_ID, settings.S3_SECRET, is_secure=True)
    url = archiveFile.locations.all()[0].url
    bucket = ""
    key = ""
    _, path = url.split(":", 1)
    path = path.lstrip("/")
    bucket, path = path.split("/", 1)
    
    return conn.generate_url(3600*24, 'GET', bucket, path)

    
def serializeGroup(user,group=None):
    groupstructure=None
    if group:
        userstructure=[]
        if user.has_perm('auth.view_group', group):
            for u in group.user_set.all():
                userstructure.append({"email":u.email})
            groupstructure={"name":group.name,"id":group.id,"users":group.user_set.all()}
    else:
        groupstructure=[]
        for group in Group.objects.all():
            userstructure=[]
            if user.has_perm('auth.view_group', group):
                for u in group.user_set.all():
                    userstructure.append({"email":u.email})
                groupstructure.append({"name":group.name,"id":group.id,"users":group.user_set.all()})
    return groupstructure


class GroupList(APIView):
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    """
    List all groups that user can see, or create a new group.
    """
    def get(self, request, format=None):
        groupstructure = serializeGroup(request.user)
        serializer = SpecialGroupSerializer(groupstructure, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        if not request.user.has_perm('auth.add_group'):
            return HttpResponseForbidden()
        sdata=[]
        for types in GROUPTYPES: 
            userstructure=[]           
            group, created = Group.objects.get_or_create(name=request.DATA['name']+"__"+types)

            self.request.user.groups.add(group)
            assign_perm('view_group', self.request.user, group)
            assign_perm('add_group', self.request.user, group)                
            assign_perm('change_group', self.request.user, group)
            assign_perm('delete_group', self.request.user, group)
    
            for u in self.request.DATA['users']:
                try:
                    user = User.objects.get(email=u["email"])
                    user.groups.add(group)
                except Exception,e:
                    print "ERROR: %s" % e
            
            for user in group.user_set.all():
                userstructure.append({"email":user.email})

            sdata.append({"name":group.name,"id":group.id,"users":userstructure}) 
        
        return Response(sdata, status=status.HTTP_201_CREATED)

class GroupDetail(APIView):
    """
    Retrieve, update or delete a Group instance.
    """
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        group = self.get_object(pk)
        if not request.user.has_perm('auth.view_group', group):
            return HttpResponseForbidden()        
        groupstructure = serializeGroup(request.user,group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        group = self.get_object(pk)
        if not request.user.has_perm('auth.change_group', group):
            return HttpResponseForbidden()        

        for u in self.request.DATA['users']:
            try:
                user = User.objects.get(email=u["email"])
                user.groups.add(group)
            except Exception,e:
                print "ERROR: %s" % e

        groupstructure = serializeGroup(request.user,group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)


    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        if not request.user.has_perm('auth.delete_group', snippet):
            return HttpResponseForbidden()        
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
# class GroupViewSet(viewsets.ModelViewSet):
#     serializer_class = GroupSerializer
#     queryset = Group.objects.all()
#     authentication_classes = (Auth0Authentication,)
#     permission_classes = (DjangoObjectPermissionsAll,)
#     filter_backends = (filters.DjangoFilterBackend,filters.DjangoObjectPermissionsFilter,)
#     filter_fields = ('name',)
#         
#     def post_save(self, obj,created=True):
#         try:
#             assign_perm('view_group', self.request.user, obj)
#             assign_perm('change_group', self.request.user, obj)
#             assign_perm('delete_group', self.request.user, obj)
#         except Exception,e:
#             return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SearchViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SearchSerializer
 
 
    def get_queryset(self, *args, **kwargs):
        # This will return a dict of the first known
        # unit of distance found in the query
        request = self.request
        queryset = EmptySearchQuerySet()

        fieldlist = []
        if request.GET.get('fields'):
            rawfields = request.GET.get('fields')
            fieldlist = rawfields.split(',')        
        
        facetlist = []
        if request.GET.get('facets'):
            rawfacets = request.GET.get('facets')
            facetlist = rawfacets.split(',')        
 
        if request.GET.get('q'):
            query = request.GET.get('q')
            sqs = SearchQuerySet()
            for item in facetlist:
                sqs = sqs.facet(item)
            if not fieldlist:            
                sqs = sqs.filter(content=query)
            else:
                for idx, field in enumerate(fieldlist):
                    if idx==0:
                        sqs = sqs.filter(SQ(**{field:query}))
                    else:    
                        sqs = sqs.filter_or(SQ(**{field:query}))
        
        finalResult=[]
        for m in list(sqs):
            if request.user.has_perm('filemaster.view_archivefile',m.object):
                finalResult.append(m)
            else:
                continue 
        
        return finalResult
    
@api_view(['GET'])
@authentication_classes((Auth0Authentication,TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def token(request):
    """
    Retrieve a token
    """

    if request.method == 'GET':
        u = User.objects.get(email=request.user.email)
        t = Token.objects.get(user=u)
        serializer = TokenSerializer(t)
        return Response(serializer.data)
