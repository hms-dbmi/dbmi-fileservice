from django.http import Http404,HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseBadRequest,HttpResponseForbidden, HttpResponseServerError, HttpResponse,HttpResponseNotFound, HttpResponseRedirect

from django.contrib.auth.models import User, Group, Permission

from rest_framework import status,filters,viewsets,mixins
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from .models import HealthCheck,GROUPTYPES,Bucket
from .authenticate import Auth0Authentication, ServiceAuthentication
from .serializers import HealthCheckSerializer,SpecialGroupSerializer,TokenSerializer

from guardian.shortcuts import assign_perm,get_objects_for_group
from django.contrib.auth import get_user_model
import string,random


import logging
log = logging.getLogger(__name__)

User = get_user_model()


def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class HealthCheckList(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('message', 'id')

    
def serializeGroup(user,group=None):
    groupstructure=None
    if group:
        userstructure=[]
        if user.has_perm('auth.view_group', group):
            for u in group.user_set.all():
                userstructure.append({"email":u.email})
            groupstructure={"name":group.name,"id":group.id,"users":group.user_set.all(),"buckets":get_objects_for_group(group, 'filemaster.write_bucket')}
    else:
        groupstructure=[]
        for group in Group.objects.all():
            userstructure=[]
            if user.has_perm('auth.view_group', group):
                for u in group.user_set.all():
                    userstructure.append({"email":u.email})
                groupstructure.append({"name":group.name,"id":group.id,"users":group.user_set.all(),"buckets":get_objects_for_group(group, 'filemaster.write_bucket')})
    return groupstructure


class GroupList(APIView):
    authentication_classes = (Auth0Authentication,TokenAuthentication,ServiceAuthentication,)
    permission_classes = (IsAuthenticated,)

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
            group, created = Group.objects.get_or_create(name=request.DATA['name']+"__"+types)

            self.request.user.groups.add(group)
            assign_perm('view_group', self.request.user, group)
            assign_perm('add_group', self.request.user, group)                
            assign_perm('change_group', self.request.user, group)
            assign_perm('delete_group', self.request.user, group)

            assign_perm('change_group', Group.objects.get(name="powerusers"), group)
    
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
    
    def getUsers(self,request,group):
        try:
            for u in request.DATA['users']:
                try:
                    user = User.objects.get(email=u["email"])
                    user.groups.add(group)
                except Exception,e:
                    print "ERROR: %s" % e
        except:
            pass
    
    def getBuckets(self,request,group):
        try:
            for u in request.DATA['buckets']:
                try:
                    bucket = Bucket.objects.get(name=u["name"])
                    assign_perm('filemaster.write_bucket', group, bucket)
                except Exception,e:
                    print "ERROR: %s" % e
        except:
            pass

    def put(self, request, pk,format=None):
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
        
        self.getUsers(self.request,group)
        self.getBuckets(self.request,group)        

        groupstructure = serializeGroup(request.user,group=group)
        serializer = SpecialGroupSerializer(groupstructure, many=False)
        return Response(serializer.data)


    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        if not request.user.has_perm('auth.delete_group', snippet):
            return HttpResponseForbidden()        
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserList(APIView):
    authentication_classes = (Auth0Authentication,TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

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
    
        for u in self.request.DATA['users']:
            try:
                user = get_user_model().objects.create_user(id_generator(16),email=u,password=id_generator(16))
                userstructure.append(user.email)
            except Exception,e:
                print "ERROR: %s" % e
        
        sdata.append({"users":userstructure}) 
        
        return Response(sdata, status=status.HTTP_201_CREATED)


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
