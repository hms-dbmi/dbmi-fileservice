from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered

from filemaster.models import ArchiveFile
from filemaster.models import Bucket
from filemaster.models import CustomUser
from filemaster.models import DownloadLog
from filemaster.models import FileLocation

from guardian.admin import GuardedModelAdmin


class CustomUserAdmin(admin.ModelAdmin):
    fields = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'groups', )
    list_display = ('username', 'email', 'is_staff', 'date_joined', )
    readonly_fields = ('date_joined', )
    search_fields = ('email', 'first_name', 'last_name', )
    sortable_by = ('is_staff', 'is_active', 'date_joined', )


admin.site.register(CustomUser, CustomUserAdmin)


class BucketAdmin(admin.ModelAdmin):
    list_display = ('name', )


admin.site.register(Bucket, BucketAdmin)


class ArchiveFileAdmin(GuardedModelAdmin):
    fields = ('creationdate', 'uuid', 'filename', 'owner', 'tags', 'locations')
    list_display = ('filename', 'uuid', 'creationdate', 'owner')
    readonly_fields = ('uuid', 'creationdate')
    sortable_by = ('owner', 'creationdate', 'modifydate')
    search_fields = ('owner', 'filename', 'metadata', )


admin.site.register(ArchiveFile, ArchiveFileAdmin)


class FileLocationAdmin(GuardedModelAdmin):
    fields = ('creationdate', 'url', 'uploadComplete', 'storagetype', 'filesize', )
    list_display = ('id', 'url', 'filesize', 'creationdate', 'storagetype')
    readonly_fields = ('creationdate', )
    search_fields = ('id', 'url')
    sortable_by = ('filesize', 'creationdate', 'modifydate', 'storagetype', 'uploadcomplete')


admin.site.register(FileLocation, FileLocationAdmin)


class DownloadLogAdmin(admin.ModelAdmin):
    fields = ('archivefile', 'download_requested_on', 'requesting_user', )
    readonly_fields = ('download_requested_on', )
    list_display = ('archivefile', 'download_requested_on', 'requesting_user', )
    sortable_by = ('archivefile', 'download_requested_on', 'requesting_user', )
    search_fields = ('archivefile', 'requesting_user', )


admin.site.register(DownloadLog, DownloadLogAdmin)


def patch_admin(model, admin_site=None):
    """
    Enables version control with full admin integration for a model that has
    already been registered with the django admin site.
    This is excellent for adding version control to existing Django contrib
    applications.
    """
    admin_site = admin_site or admin.site

    try:
        ModelAdmin = admin_site._registry[model].__class__
    except KeyError:
        raise NotRegistered("The model %r has not been registered with the admin site." % model)

    # Unregister existing admin class.
    admin_site.unregister(model)

    # Register patched admin class.
    class PatchedModelAdmin(GuardedModelAdmin, ModelAdmin): # Remove VersionAdmin, if you don't use reversion.
        pass

    admin_site.register(model, PatchedModelAdmin)


patch_admin(Group)
