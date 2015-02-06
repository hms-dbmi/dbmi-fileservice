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
from boto.s3.connection import S3Connection

@shared_task
def glacierLifecycleMove(locationstring,pid):
    status = False
    af = ArchiveFile.objects.get(id=pid)
    url= locationstring
    loc = af.locations.all()[0]
    bucket,path = loc.get_bucket()

    try:
        AWS_KEY_ID = settings.BUCKETS[bucket]["AWS_KEY_ID"]
    except:
        AWS_KEY_ID=None
        
    try:
        AWS_SECRET = settings.BUCKETS[bucket]["AWS_SECRET"]
    except:
        AWS_SECRET=None
    
    if not AWS_KEY_ID:
        return False
    
    c = S3Connection(AWS_KEY_ID, AWS_SECRET, is_secure=True)
    bucket = c.get_bucket(bucket,validate=False)

    to_glacier = Transition(date=datetime.combine(af.expirationdate,datetime.min.time()).isoformat(), storage_class='GLACIER')
    rule = Rule(str(uuid.uuid4()), path, 'Enabled', transition=to_glacier)
    lifecycle=None
    try:
        lifecycle = bucket.get_lifecycle_config()
    except:
        lifecycle = Lifecycle()
    
    if not lifecycle:
        lifecycle=Lifecycle()
    
    lifecycle.append(rule)
    status = bucket.configure_lifecycle(lifecycle)

    if status:
        loc = af.locations.all()[0]
        loc.storagetype="glacier"
        loc.save()

    return status

@shared_task
def glacierVaultMove(locationstring,id):
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
    
    c = S3Connection(aws_key, aws_secret, is_secure=True)
    bucket = c.get_bucket(bucket,validate=False)


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