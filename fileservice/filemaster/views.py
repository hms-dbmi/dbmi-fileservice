import string
import random
from furl import furl

from django.shortcuts import render, reverse
from django.http import Http404, HttpResponseForbidden
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from guardian.shortcuts import assign_perm, get_objects_for_group
from django.contrib.auth import get_user_model

from dbmi_client.authn import DBMIModelUser
from dbmi_client.auth import dbmi_user
from dbmi_client.authn import logout_redirect

from filemaster.models import GROUPTYPES, Bucket
from filemaster.serializers import SpecialGroupSerializer, TokenSerializer

import logging
log = logging.getLogger(__name__)

# Get the current user model
User = get_user_model()


@dbmi_user
def logout(request):

    # Send them back to index should they log in again
    next_url = request.build_absolute_uri(reverse('filemaster:index'))

    # Log them out
    return logout_redirect(request, next_url)


@dbmi_user
def index(request):

    # Get the user
    user = request.user

    # Get their token
    token = Token.objects.get_or_create(user=user)[0].key

    # Get the URL
    fileservice_url = furl(request.build_absolute_uri())
    fileservice_url.path.segments.clear()
    fileservice_url.query.params.clear()

    # Set the context
    context = {
        'token': token,
        'user': user,
        'fileservice_url': fileservice_url.url,
    }

    return render(request, template_name='filemaster/index.html', context=context)


def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

    
def serializeGroup(user, group=None):
    groupstructure=None
    if group:
        userstructure=[]
        if user.has_perm('auth.view_group', group):
            for u in group.user_set.all():
                userstructure.append({"email":u.email})
            groupstructure={"name":group.name, "id":group.id, "users":group.user_set.all(), "buckets":get_objects_for_group(group, 'filemaster.write_bucket')}
    else:
        groupstructure=[]
        for group in Group.objects.all():
            userstructure=[]
            if user.has_perm('auth.view_group', group):
                for u in group.user_set.all():
                    userstructure.append({"email":u.email})
                groupstructure.append({"name":group.name, "id":group.id, "users":group.user_set.all(), "buckets":get_objects_for_group(group, 'filemaster.write_bucket')})
    return groupstructure


class GroupList(APIView):
    """
    List all groups that user can see, or create a new group.
    """
    def get(self, request, format=None):

        log.debug("[views][GroupList][get]")

        groupstructure = serializeGroup(request.user)
        serializer = SpecialGroupSerializer(groupstructure, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        if not request.user.has_perm('auth.add_group'):
            return HttpResponseForbidden()
        sdata=[]
        for types in GROUPTYPES: 
            userstructure=[]           
            group, created = Group.objects.get_or_create(name=request.data['name']+"__"+types)

            self.request.user.groups.add(group)
            assign_perm('view_group', self.request.user, group)
            assign_perm('add_group', self.request.user, group)                
            assign_perm('change_group', self.request.user, group)
            assign_perm('delete_group', self.request.user, group)

            assign_perm('change_group', Group.objects.get(name="powerusers"), group)
    
            for u in self.request.data['users']:
                try:
                    user = User.objects.get(email=u["email"])
                    user.groups.add(group)
                except Exception as e:
                    log.error("ERROR: %s" % e)
            
            for user in group.user_set.all():
                userstructure.append({"email":user.email})

            sdata.append({"name":group.name, "id":group.id, "users":userstructure})
        
        return Response(sdata, status=status.HTTP_201_CREATED)


class GroupDetail(APIView):
    """
    Retrieve, update or delete a Group instance.
    """

    def get_object(self, pk):
        try:
            return Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        group = self.get_object(pk)
        if not request.user.has_perm('auth.view_group', group):
            return HttpResponseForbidden()        
        groupstructure = serializeGroup(request.user, group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)
    
    def getUsers(self, request, group):
        try:
            for u in request.data['users']:
                try:
                    user = User.objects.get(email=u["email"])
                    user.groups.add(group)
                except Exception as e:
                    log.error("ERROR: %s" % e)
        except Exception as e:
            log.error('Could not add user to group: {}'.format(e))
    
    def getBuckets(self, request, group):
        try:
            for u in request.data['buckets']:
                try:
                    bucket = Bucket.objects.get(name=u["name"])
                    assign_perm('filemaster.write_bucket', group, bucket)
                except Exception as e:
                    log.error("ERROR: %s" % e)
        except:
            pass

    def put(self, request, pk, format=None):
        if pk.isdigit():
            group = self.get_object(pk)
        elif "__" in pk:
            group = Group.objects.get(name=pk)
        else:
            return HttpResponseForbidden()
            
        if not group:
            return HttpResponseForbidden()
            
        if not request.user.has_perm('auth.change_group', group):
            return HttpResponseForbidden()
        
        self.getUsers(self.request, group)
        self.getBuckets(self.request, group)

        groupstructure = serializeGroup(request.user, group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)

    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        if not request.user.has_perm('auth.delete_group', snippet):
            return HttpResponseForbidden()        
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserList(APIView):
    """
    List all groups that user can see, or create a new group.
    """
    def get(self, request, format=None):
        return Response([])

    def post(self, request, format=None):
        if not request.user.has_perm('filemaster.add_customuser'):
            return HttpResponseForbidden()

        sdata=[]
        userstructure=[]
    
        for u in self.request.data['users']:
            try:
                user = get_user_model().objects.create_user(id_generator(16), email=u, password=id_generator(16))
                userstructure.append(user.email)
            except Exception as e:
                log.error("ERROR: %s" % e)
        
        sdata.append({"users":userstructure}) 
        
        return Response(sdata, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes((DBMIModelUser, ))
def token(request):
    """
    Retrieve a token
    """

    if request.method == 'GET':
        u = User.objects.get(email=request.user.email)
        t = Token.objects.get(user=u)
        serializer = TokenSerializer(t)
        return Response(serializer.data)
