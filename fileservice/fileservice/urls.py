from django.conf.urls import include, url
from django.shortcuts import redirect, reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^filemaster/',include('filemaster.urls', namespace='filemaster')),
    url(r'^healthcheck/?', include('health_check.urls')),
    url(r'^dbmi-auth/', include('dbmi_client.login.urls', namespace='dbmi_auth')),
    url(r'^$', lambda r: redirect(reverse('filemaster:index'))),
]

