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
from .authenticate import ExampleAuthentication
from .serializers import HealthCheckSerializer,UserSerializer
#from .permissions import DjangoObjectPermissionsAll,DjangoModelPermissionsAll,DjangoObjectPermissionsChange
from guardian.shortcuts import assign_perm

class HealthCheckList(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    authentication_classes = (ExampleAuthentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,filters.DjangoObjectPermissionsFilter,)
