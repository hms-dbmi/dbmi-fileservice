from django.conf.urls import patterns, include, url
from django.contrib.auth import views
from rest_framework.urlpatterns import format_suffix_patterns
from .views import HealthCheckList,GroupList,GroupDetail,ArchiveFileList,UserList
from rest_framework.routers import DefaultRouter
from rest_framework import renderers


router = DefaultRouter()
router.register(r'healthcheck', HealthCheckList)
router.register(r'file', ArchiveFileList)


urlpatterns = patterns(
                       'filemaster.views',
                       url(r'^groups/$', GroupList.as_view()),
                       url(r'^user/$', UserList.as_view()),
                       url(r'^groups/(?P<pk>[^/]+)/$', GroupDetail.as_view()),
                       url(r'^token/$', 'token'),                                              
                       url(r'^api/', include(router.urls)),

)
