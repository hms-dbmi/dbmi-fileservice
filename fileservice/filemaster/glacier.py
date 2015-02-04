from django.contrib.auth.models import User 
from django.contrib.auth import get_user_model
from django.conf import settings
from filemaster.tasks import glaciermove
user = get_user_model()        

from .models import ArchiveFile,FileLocation,Bucket
import json,uuid
from datetime import date,datetime,timedelta

today = date.today()
daysago =  today - timedelta(days=10)


for af in ArchiveFile.objects.filter(expirationdate__gt=daysago,expirationdate__lt=today):
    copysuccessful = False
    try:
        if af.locations.all()[0].startswith("s3://") or af.locations.all()[0].startswith("S3://"):
            glaciermove.delay(af.locations.all()[0],af.id)
    except Exception,e:
        print e
    

# get all files with expire between today and 3 days ago
# for each file: 
#   copy to Glacier
#   get id
#   change location of file
#   delete from s3 