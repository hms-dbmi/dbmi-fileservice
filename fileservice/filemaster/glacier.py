from __future__ import absolute_import

import os

from django.conf import settings

import json,uuid
from datetime import date,datetime,timedelta

from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

import os
import sys

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

User = get_user_model()

today = date.today()
daysago =  today - timedelta(days=10)

from filemaster.tasks import *
from filemaster.models import *


for af in ArchiveFile.objects.filter(expirationdate__gt=daysago,expirationdate__lt=today):
    copysuccessful = False
    try:
        if (af.locations.all()[0].url.startswith("s3://") or af.locations.all()[0].url.startswith("S3://")) and af.locations.all()[0].storagetype!="glacier":
            glaciermove.delay(af.locations.all()[0].url,af.id)
    except Exception,e:
        print e
