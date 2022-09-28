from rest_framework.routers import DefaultRouter

from django.urls import include
from django.urls import re_path

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
from .files import FileOperationList

from filemaster.realignment import CreateRealignedFile
from filemaster.uploader import UploaderComplete, UploaderCheck, UploaderMetadata

app_name = FilemasterConfig.name

router = DefaultRouter()
router.register(r'file', ArchiveFileList)
router.register(r'file-operation', FileOperationList)

urlpatterns = [
    re_path(r'^groups?/?$', GroupList.as_view()),
    re_path(r'^groups?/(?P<pk>[^/]+)/?$', GroupDetail.as_view()),
    re_path(r'^user/$', UserList.as_view()),
    re_path(r'^token/?$', token, name="token"),
    re_path(r'^realignment/new$', CreateRealignedFile.as_view(), name='realignment_new'),
    re_path(r'^uploader/complete$', UploaderComplete.as_view(), name='uploader_complete'),
    re_path(r'^uploader/check$', UploaderCheck.as_view(), name='uploader_check'),
    re_path(r'^uploader/metadata$', UploaderMetadata.as_view(), name='uploader_metadata'),
    re_path(r'^api/', include(router.urls)),
    re_path(r'^api/logs/?$', DownloadLogList.as_view()),
    re_path(r'^api/location/?$', FileLocationList.as_view()),
    re_path(r'^api/location/(?P<pk>[^/]+)/?$', FileLocationDetail.as_view()),
    re_path(r'^api/file-detail/(?P<pk>[^/]+)/?$', ArchiveFileDetail.as_view()),
    re_path(r'^api/file-search/?$', ArchiveFileSearch.as_view()),
    re_path(r'^logout/?$', logout, name="logout"),
    re_path(r'^$', index, name="index"),
]
