from django.conf.urls import include, url
from .views import GroupList, GroupDetail, UserList, token, index, logout
from .files import ArchiveFileList
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'file', ArchiveFileList)

urlpatterns = [
    url(r'^groups/$', GroupList.as_view()),
    url(r'^user/$', UserList.as_view()),
    url(r'^groups/(?P<pk>[^/]+)/$', GroupDetail.as_view()),
    url(r'^token/$', token, name="token"),
    url(r'^api/', include(router.urls)),
    url(r'^logout/$', logout, name="logout"),
    url(r'^$', index, name="index"),
]
