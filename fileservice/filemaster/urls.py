from rest_framework.routers import DefaultRouter

from django.conf.urls import include
from django.conf.urls import url

from filemaster.apps import FilemasterConfig
from .views import GroupDetail
from .views import GroupList
from .views import UserList
from .views import token
from .views import index
from .views import logout
from .views import BucketViewSet

from .files import ArchiveFileList
from .files import DownloadLogList

app_name = FilemasterConfig.name

router = DefaultRouter()
router.register(r'file', ArchiveFileList)
router.register(r'bucket', BucketViewSet)

urlpatterns = [
    url(r'^groups?/?$', GroupList.as_view()),
    url(r'^groups?/(?P<pk>[^/]+)/?$', GroupDetail.as_view()),
    url(r'^user/$', UserList.as_view()),
    url(r'^token/?$', token, name="token"),
    url(r'^api/', include(router.urls)),
    url(r'^api/logs/?$', DownloadLogList.as_view()),
    url(r'^logout/?$', logout, name="logout"),
    url(r'^$', index, name="index"),
]
