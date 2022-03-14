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

from .files import ArchiveFileList
from .files import ArchiveFileDetail
from .files import ArchiveFileSearch
from .files import DownloadLogList
from .files import FileLocationList
from .files import FileLocationDetail

from filemaster.uploader import Uploader
from fileservice.view import Healthcheck

app_name = FilemasterConfig.name

router = DefaultRouter()
router.register(r'file', ArchiveFileList)
router.register(r'healthcheck', Healthcheck)
router.register(r'uploader', Uploader)

urlpatterns = [
    url(r'^groups?/?$', GroupList.as_view()),
    url(r'^groups?/(?P<pk>[^/]+)/?$', GroupDetail.as_view()),
    url(r'^user/$', UserList.as_view()),
    url(r'^token/?$', token, name="token"),
    url(r'^api/', include(router.urls)),
    url(r'^api/logs/?$', DownloadLogList.as_view()),
    url(r'^api/location/?$', FileLocationList.as_view()),
    url(r'^api/location/(?P<pk>[^/]+)/?$', FileLocationDetail.as_view()),
    url(r'^api/file-detail/(?P<pk>[^/]+)/?$', ArchiveFileDetail.as_view()),
    url(r'^api/file-search/?$', ArchiveFileSearch.as_view()),
    url(r'^logout/?$', logout, name="logout"),
    url(r'^$', index, name="index"),
]
