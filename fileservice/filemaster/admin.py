from django.contrib import admin
from .models import CustomUser, Bucket, ArchiveFile, FileLocation
from guardian.admin import GuardedModelAdmin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered


class CustomUserAdmin(admin.ModelAdmin):
    fields = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'groups', )
    list_display = ('username', 'email', 'is_staff')


class BucketAdmin(admin.ModelAdmin):
    fields = ('name', 'permissions', )
    list_display = ('name', )


class ArchiveFileAdmin(admin.ModelAdmin):
    fields = ('creationdate', 'uuid', 'filename', 'owner', 'tags', )
    list_display = ('filename', 'uuid', 'creationdate', 'owner')


class FileLocationAdmin(admin.ModelAdmin):
    fields = ('creationdate', 'url', 'uploadComplete', 'storagetype', 'filesize', )
    list_display = ('url', 'filesize', 'creationdate', 'storagetype')


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
    

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Bucket, BucketAdmin)
admin.site.register(ArchiveFile, ArchiveFileAdmin)
admin.site.register(FileLocation, FileLocationAdmin)
patch_admin(Group)

