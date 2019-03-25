import datetime
from datetime import timedelta
from datetime import date
from jsonfield import JSONField
import logging
import re
import random
import string
import urllib.request
import urllib.parse
import urllib.error
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import UserManager
from django.core import validators
from django.core.mail import send_mail
from django.db import models
from django.db.models import UUIDField
from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework.authtoken.models import Token
from guardian.shortcuts import assign_perm
from guardian.shortcuts import remove_perm
from guardian.shortcuts import get_groups_with_perms
from taggit.managers import TaggableManager

log = logging.getLogger(__name__)

EXPIRATIONDATE = 60
if settings.EXPIRATIONDATE:
    EXPIRATIONDATE = settings.EXPIRATIONDATE

GROUPTYPES = ["ADMINS", "DOWNLOADERS", "READERS", "WRITERS", "UPLOADERS"]


def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


class FileLocation(models.Model):
    creationdate = models.DateTimeField(auto_now=False, auto_now_add=True)
    modifydate = models.DateTimeField(auto_now=True, auto_now_add=False)
    url = models.TextField(blank=False, null=False)
    uploadComplete = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    storagetype = models.CharField(blank=True, null=True, max_length=255)
    filesize = models.BigIntegerField(blank=True, null=True)

    class Meta:
        ordering = ('-creationdate',)

    def __str__(self):
        return "%s" % (self.id)

    def get_bucket(self):
        bucket = None
        path = None
        if self.url.startswith("s3://") or self.url.startswith("S3://"):
            bucket = ""
            _, path = self.url.split(":", 1)
            path = path.lstrip("/")
            bucket, path = path.split("/", 1)
        return bucket, path


class Bucket(models.Model):
    name = models.CharField(max_length=255, blank=False, null=False, unique=True)

    def __str__(self):
        return "%s" % (self.name)

    class Meta:
        permissions = (
            ('write_bucket', 'Write to bucket'),
        )    


class ArchiveFile(models.Model):
    uuid = UUIDField(default=uuid.uuid4, editable=False)
    description = models.CharField(max_length=255, blank=True, null=True, default='')
    filename = models.TextField()
    metadata = JSONField(blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL)
    locations = models.ManyToManyField(FileLocation)
    creationdate = models.DateTimeField(auto_now=False, auto_now_add=True)
    modifydate = models.DateTimeField(auto_now=True, auto_now_add=False)
    expirationdate = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)

    tags = TaggableManager()

    def save(self, *args, **kwargs):
        # Check if the row with this hash already exists.
        if not self.pk and not self.expirationdate:
            self.expirationdate = date.today() + timedelta(days=EXPIRATIONDATE) 
        super(ArchiveFile, self).save(*args, **kwargs)

    def setDefaultPerms(self, group, types):
        try:
            g = Group.objects.get(name=group+"__"+types)
            if types == "ADMINS":
                assign_perm('view_archivefile', g, self)
                assign_perm('add_archivefile', g, self)
                assign_perm('change_archivefile', g, self)
                assign_perm('delete_archivefile', g, self)
                assign_perm('download_archivefile', g, self)
                assign_perm('upload_archivefile', g, self)
            elif types == "READERS":
                assign_perm('view_archivefile', g, self)
            elif types == "WRITERS":
                assign_perm('add_archivefile', g, self)
                assign_perm('change_archivefile', g, self)
            elif types == "UPLOADERS":
                assign_perm('upload_archivefile', g, self)
            elif types == "DOWNLOADERS":
                assign_perm('download_archivefile', g, self)
        except Exception as e:
            log.error("ERROR setperms %s %s %s" % (e, group, types))
            return         

    def removeDefaultPerms(self, group, types):
        try:
            g = Group.objects.get(name=group+"__"+types)
            if types == "ADMINS":
                remove_perm('view_archivefile', g, self)
                remove_perm('add_archivefile', g, self)
                remove_perm('change_archivefile', g, self)
                remove_perm('delete_archivefile', g, self)
                remove_perm('download_archivefile', g, self)
                remove_perm('upload_archivefile', g, self)
            elif types == "READERS":
                remove_perm('view_archivefile', g, self)
            elif types == "WRITERS":
                remove_perm('add_archivefile', g, self)
                remove_perm('change_archivefile', g, self)
            elif types == "UPLOADERS":
                remove_perm('upload_archivefile', g, self)
            elif types == "DOWNLOADERS":
                remove_perm('download_archivefile', g, self)
        except Exception as e:
            log.error("ERROR %s" % e)
            return         

    def setPerms(self, permissions):
        for types in GROUPTYPES:
            self.setDefaultPerms(permissions, types)

    def killPerms(self):
        for groupname in self.get_permissions_display():
            for types in GROUPTYPES:
                self.removeDefaultPerms(groupname, types)

    def get_tags_display(self):
        return self.tags.values_list('name', flat=True)

    def get_permissions_display(self):
        grouplist = []
        for g in  get_groups_with_perms(self):
            try:
                begin = g.name.find("__")
                groupname = g.name[0:begin]
                if groupname not in grouplist:
                    grouplist.append(groupname)
            except:
                log.error("Error with %s" % g.name)
        return grouplist

    def get_location(self, bucket):

        # If only one location, return it
        if not len(self.locations.all()) == 1:
            return next(iter(self.locations.all()))

        # Walk through locations and match bucket
        for location in self.locations.all():

            # Check bucket
            if location.get_bucket()[0].lower() == bucket.lower():
                return location

        return None

    def __str__(self):
        return "%s" % (self.uuid)

    class Meta:
        permissions = (
            ('download_archivefile', 'Download File'),
            ('upload_archivefile', 'Upload File'),
        )


def get_anonymous_user_instance(User):
    return User(
        username='',
        email='AnonymousUser',
        password='!k1IjmeTmhVLJsfPIQ5l1ojH1U1PzgI0IjGvqm0Cd',
        is_active=True,
        last_login=datetime.date(1970, 1, 1),
        date_joined=datetime.date(1970, 1, 1),
    )


class CustomUser(AbstractBaseUser, PermissionsMixin):

    username = models.CharField(
        _('username'),
        max_length=191,
        unique=True,
        help_text=_('Required. 191 characters or fewer. Letters, numbers and @/./+/-/_/| characters'),
        validators=[
            validators.RegexValidator(re.compile('^[\w.@+-|]+$'), _('Enter a valid username.'), 'invalid')
        ]
    )

    first_name = models.CharField(_('first name'), max_length=254, blank=True)
    last_name = models.CharField(_('last name'), max_length=254, blank=True)
    email = models.EmailField(_('email address'), max_length=254, unique=True)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    )

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_absolute_url(self):
        return "/users/%s/" % urllib.parse.quote(self.username)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create a token for each created user
    """
    if created and instance.email is not 'AnonymousUser':
        Token.objects.get_or_create(user=instance)


def location_changed(sender, instance, action, reverse, model, pk_set,**kwargs):
    from .tasks import glacierLifecycleMove

    if action == "post_add":
        af = instance
        for p in pk_set:
            loc = FileLocation.objects.get(id=p)
            bucket, path = loc.get_bucket()
            glaciertype = "lifecycle"
            try:
                glaciertype = settings.BUCKETS[bucket]["glaciertype"]
            except:
                pass
            if bucket and glaciertype == "lifecycle":
                pass

m2m_changed.connect(location_changed, sender=ArchiveFile.locations.through)


class DownloadLog(models.Model):
    """
    A model used to track when a user has requested a file download.
    """

    archivefile = models.ForeignKey(ArchiveFile, blank=False, null=False, on_delete=models.PROTECT)
    download_requested_on = models.DateTimeField(blank=False, null=False, auto_now_add=True)
    requesting_user = models.ForeignKey(CustomUser, blank=False, null=False, on_delete=models.PROTECT)
    requesting_email = models.EmailField(blank=True, null=True, help_text='Since the user might be a service account, this field helps track where the original request came from.')
