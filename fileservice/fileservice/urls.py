from django.shortcuts import redirect, reverse
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.conf.urls import url, include
from django.views.defaults import permission_denied

from .views import Healthcheck

admin.autodiscover()

urlpatterns = [
    url(r'^admin/login/', permission_denied, {'exception': PermissionDenied('Permission Denied')}),
    url(r'^admin/', admin.site.urls, name='admin'),
    url(r'^filemaster/', include('filemaster.urls', namespace='filemaster')),
    url(r'^healthcheck/?', Healthcheck.as_view(), name='healthcheck'),
    url(r'^dbmi-auth/', include('dbmi_client.login.urls')),
    url(r'^$', lambda r: redirect(reverse('filemaster:index'))),
]
