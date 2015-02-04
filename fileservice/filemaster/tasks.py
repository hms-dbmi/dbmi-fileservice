from __future__ import absolute_import

from celery import shared_task

from django.contrib.auth.models import User 
from django.contrib.auth import get_user_model
from django.conf import settings
user = get_user_model()        

from .models import ArchiveFile,FileLocation,Bucket
import json,uuid,boto
from datetime import date,datetime,timedelta
from boto.s3.lifecycle import Lifecycle, Transition, Rule
#from filemaster.tasks import add
#add.delay(2, 2)

@shared_task
def glaciermove(locationstring,id):
    status = False
    af = ArchiveFile.objects.get(id=id)
    url= locationstring

    bucket = ""
    key = ""
    _, path = url.split(":", 1)
    path = path.lstrip("/")
    bucket, path = path.split("/", 1)

    aws_key=settings.BUCKETS[bucket]["AWS_KEY_ID"]
    aws_secret=settings.BUCKETS[bucket]["AWS_SECRET"]
    
    c = boto.connect_s3(aws_key, aws_secret, is_secure=True)
    bucket = c.get_bucket(bucket)

    to_glacier = Transition(days=1, storage_class='GLACIER')
    rule = Rule(str(uuid.uuid4()), path, 'Enabled', transition=to_glacier)
    lifecycle = Lifecycle()
    lifecycle.append(rule)
    status = bucket.configure_lifecycle(lifecycle)

    if status:
        loc = af.locations.all()[0]
        loc.storagetype="glacier"
        loc.save()

    return status

@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)