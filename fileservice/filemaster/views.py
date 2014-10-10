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


from .models import HealthCheck
from .authenticate import ExampleAuthentication,Auth0Authentication
from .serializers import HealthCheckSerializer,UserSerializer,GroupSerializer,SpecialGroupSerializer
from .permissions import DjangoObjectPermissionsAll,DjangoModelPermissionsAll,DjangoObjectPermissionsChange
from rest_framework_extensions.mixins import DetailSerializerMixin
from guardian.shortcuts import assign_perm
from django.contrib.auth import get_user_model

GROUPTYPES=["READ","WRITE","ADMIN"]
User = get_user_model()        

class HealthCheckList(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    authentication_classes = (Auth0Authentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('message', 'id')

def serializeGroup(user,group=None):
    groupstructure=None
    if group:
        userstructure=[]
        if user.has_perm('auth.view_group', group):
            for u in group.user_set.all():
                userstructure.append({"id":u.id,"email":u.email})
            groupstructure={"name":group.name,"id":group.id,"users":userstructure}
    else:
        groupstructure=[]
        for group in Group.objects.all():
            userstructure=[]
            if user.has_perm('auth.view_group', group):
                for u in group.user_set.all():
                    userstructure.append({"id":u.id,"email":u.email})
                groupstructure.append({"name":group.name,"id":group.id,"users":userstructure})
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
                    user = User.objects.get(id=u)
                    user.groups.add(group)
                except Exception,e:
                    print "ERROR: %s" % e
            
            for user in group.user_set.all():
                userstructure.append({"id":user.id,"email":user.email})

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
                user = User.objects.get(id=u)
                user.groups.add(group)
            except Exception,e:
                print "ERROR: %s" % e

        groupstructure = serializeGroup(request.user,group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)


#    def put(self, request, pk, format=None):
#        snippet = self.get_object(pk)
#        serializer = SnippetSerializer(snippet, data=request.DATA)
#        if serializer.is_valid():
#            serializer.save()
#            return Response(serializer.data)
#        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


