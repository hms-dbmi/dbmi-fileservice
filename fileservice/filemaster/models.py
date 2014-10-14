from __future__ import unicode_literals
import re,urllib,json

from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin,
                                        UserManager)
from django.core.mail import send_mail
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save,post_syncdb
#from uuidfield import UUIDField
from django_extensions.db.fields import UUIDField
from jsonfield import JSONField
from django.contrib.auth.models import User,Group


from guardian.shortcuts import assign_perm,remove_perm
from rest_framework.authtoken.models import Token
import random,string
from django.conf import settings

from taggit.managers import TaggableManager


GROUPTYPES=["ADMINS","DOWNLOADERS","READERS","WRITERS","UPLOADERS"]

def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class FileLocation(models.Model):
    creationdate = models.DateTimeField(auto_now=False, auto_now_add=True)
    modifydate = models.DateTimeField(auto_now=True, auto_now_add=False)
    url = models.TextField(blank=False,null=False)

    class Meta:
        ordering = ('-creationdate',)

    def __unicode__(self):
        return "%s" % (self.id)
 
 
class ArchiveFile(models.Model):
    uuid = UUIDField()
    description = models.CharField(max_length=255,blank=True,null=True)
    filename = models.TextField()
    metadata=JSONField(blank=True,null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,blank=True,null=True)
    locations = models.ManyToManyField(FileLocation)
    
    tags = TaggableManager()

    def save(self, *args, **kwargs):
        if self.pk is not None:
            super(ArchiveFile,self).save(*args, **kwargs)
            self.setPerms()
        else:
            #extra stuff like permissions
            super(ArchiveFile,self).save(*args, **kwargs)
            self.setPerms()

    def setDefaultPerms(self,group,types):
        try:
            g = Group.objects.get(name=group+"__"+types)
            if types=="ADMINS":
                assign_perm('view_archivefile', g, self)
                assign_perm('add_archivefile', g, self)                
                assign_perm('change_archivefile', g, self)
                assign_perm('delete_archivefile', g, self)            
                assign_perm('download_archivefile', g, self)            
            elif types=="READERS":
                assign_perm('view_archivefile', g, self)
            elif types=="WRITERS":
                assign_perm('change_archivefile', g, self)
                assign_perm('upload_archivefile', g, self)                
            elif types=="UPLOADERS":
                assign_perm('upload_archivefile', g, self)                
            elif types=="DOWNLOADERS":
                assign_perm('download_archivefile', g, self)
        except Exception,e:
            print "ERROR %s" % e
            return         
            
    def setPerms(self):
        if self.metadata and self.metadata["permissions"]:
            for g in self.metadata["permissions"]:
                for types in GROUPTYPES:
                    self.setDefaultPerms(g,types)


    def get_tags_display(self):
        return self.tags.values_list('name', flat=True)

    def __unicode__(self):
        return "%s" % (self.uuid)

    class Meta:
        permissions = (
            ('download_archivefile', 'Download File'),
            ('upload_archivefile', 'Upload File'),
        )


class HealthCheck(models.Model):
    message = models.CharField(max_length=255)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    A custom user class that basically mirrors Django's `AbstractUser` class
    and doesn't force `first_name` or `last_name` with sensibilities for
    international names.

    http://www.w3.org/International/questions/qa-personal-names
    """
    username = models.CharField(_('username'), max_length=30, unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, numbers and '
                    '@/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(re.compile('^[\w.@+-]+$'), _('Enter a valid username.'), 'invalid')
        ])
    first_name = models.CharField(_('first name'), max_length=254, blank=True)
    last_name = models.CharField(_('last name'), max_length=254, blank=True)
    email = models.EmailField(_('email address'), max_length=254, unique=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS =['username']
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __unicode__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if self.pk is None:
            super(CustomUser, self).save(*args, **kwargs)
            Token.objects.create(user=self)
        else:
            super(CustomUser, self).save(*args, **kwargs)  

    def get_absolute_url(self):
        return "/users/%s/" % urllib.quote(self.username)

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
