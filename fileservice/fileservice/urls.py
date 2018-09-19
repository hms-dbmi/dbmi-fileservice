from django.conf.urls import include, url
from django.conf import settings

from rest_framework.authtoken import views as rest_framework_views

from .views import callback, login

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^callback/',callback),
    url(r'^api-auth/login/', login, name='login'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    #url(r'', include('social_auth.urls')),
    url(r'^filemaster/',include('filemaster.urls', namespace='filemaster')),
    url(r'^api-token-auth/', rest_framework_views.obtain_auth_token, name='get_auth_token'),
    url(r'^healthcheck/?', include('health_check.urls')),
    url(r'', login),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls))]

