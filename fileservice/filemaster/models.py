from __future__ import unicode_literals
import re,urllib

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

from guardian.shortcuts import assign_perm,remove_perm
from rest_framework.authtoken.models import Token
import random,string

from taggit.managers import TaggableManager


GROUPTYPES=["ADMINS","DOWNLOADERS","READERS","WRITERS"]

def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
 
class ArchiveFile(models.Model):
    uuid = UUIDField()
    description = models.CharField(max_length=255,blank=True,null=True)
    metadata=JSONField(blank=True,null=True)
    
    tags = TaggableManager()

    def get_tags_display(self):
        return self.tags.values_list('name', flat=True)

    def __unicode__(self):
        return "%s" % (self.id)

    class Meta:
        permissions = (
            ('download_archivefile', 'Download File'),
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
