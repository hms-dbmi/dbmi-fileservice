from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

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
from .files import DownloadLogList
from filemaster.files import MultipartUploadViewSet, UploadPartViewSet

app_name = FilemasterConfig.name

router = DefaultRouter()
router.register(r'file', ArchiveFileList)
multipart_router = routers.NestedSimpleRouter(router, r'file', lookup='archivefile')
multipart_router.register(r'multipart', MultipartUploadViewSet)
parts_router = routers.NestedSimpleRouter(multipart_router, r'multipart', lookup='upload')
parts_router.register(r'part', UploadPartViewSet)

urlpatterns = [
    url(r'^groups?/?$', GroupList.as_view()),
    url(r'^groups?/(?P<pk>[^/]+)/?$', GroupDetail.as_view()),
    url(r'^user/$', UserList.as_view()),
    url(r'^token/?$', token, name="token"),
    url(r'^api/', include(router.urls)),
    url(r'^api/', include(multipart_router.urls)),
    url(r'^api/', include(parts_router.urls)),
    url(r'^api/logs/?$', DownloadLogList.as_view()),
    url(r'^logout/?$', logout, name="logout"),
    url(r'^$', index, name="index"),
]
