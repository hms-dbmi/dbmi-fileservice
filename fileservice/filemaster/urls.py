from django.conf.urls import patterns, include, url
from django.contrib.auth import views
from rest_framework.urlpatterns import format_suffix_patterns
from .views import HealthCheckList
from rest_framework.routers import DefaultRouter
from rest_framework import renderers


router = DefaultRouter()
router.register(r'healthcheck', HealthCheckList)

urlpatterns = patterns(
                       'filemaster.views',
                       url(r'^api/', include(router.urls)),
)
