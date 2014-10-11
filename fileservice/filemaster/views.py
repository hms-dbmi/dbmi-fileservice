from django.shortcuts import render
from django.db import models
from django.http import Http404,HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError, HttpResponse, HttpResponseRedirect
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

from rest_framework import status,filters,viewsets
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import detail_route, list_route


from .models import HealthCheck,GROUPTYPES,ArchiveFile
from .authenticate import ExampleAuthentication,Auth0Authentication
from .serializers import HealthCheckSerializer,UserSerializer,GroupSerializer,SpecialGroupSerializer,ArchiveFileSerializer
from .permissions import DjangoObjectPermissionsAll,DjangoModelPermissionsAll,DjangoObjectPermissionsChange
from rest_framework_extensions.mixins import DetailSerializerMixin
from guardian.shortcuts import assign_perm
from django.contrib.auth import get_user_model

User = get_user_model()        

class HealthCheckList(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    authentication_classes = (Auth0Authentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('message', 'id')

class ArchiveFileList(viewsets.ModelViewSet):
    queryset = ArchiveFile.objects.all()
    serializer_class = ArchiveFileSerializer
    lookup_field = 'uuid'    
    authentication_classes = (Auth0Authentication,)
    permission_classes = (DjangoObjectPermissionsChange,)
    filter_backends = (filters.DjangoFilterBackend,filters.DjangoObjectPermissionsFilter,)
    filter_fields = ('uuid',)

    def pre_save(self, obj):
        obj.owner = self.request.user

    def post_save(self, *args, **kwargs):
        if 'tags' in self.request.DATA:
            self.object.tags.set(*self.request.DATA['tags']) # type(self.object.tags) == <taggit.managers._TaggableManager>
        return super(ArchiveFileList, self).post_save(*args, **kwargs)        

    @detail_route(methods=['get'])
    def download(self, request, uuid=None):
        return Response({'status': 'password set'})


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
    authentication_classes = (Auth0Authentication,)
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
    authentication_classes = (Auth0Authentication,)
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


