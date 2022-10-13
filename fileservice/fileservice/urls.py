from django.shortcuts import redirect, reverse
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.urls import re_path, include
from django.views.defaults import permission_denied

admin.autodiscover()

urlpatterns = [
    re_path(r'^admin/login/', permission_denied, {'exception': PermissionDenied('Permission Denied')}),
    re_path(r'^admin/', admin.site.urls, name='admin'),
    re_path(r'^filemaster/',include('filemaster.urls', namespace='filemaster')),
    re_path(r'^healthcheck/?', include('health_check.urls')),
    re_path(r'^dbmi-auth/', include('dbmi_client.login.urls')),
    re_path(r'^$', lambda r: redirect(reverse('filemaster:index'))),
]
