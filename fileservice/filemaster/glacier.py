from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.wsgi import get_wsgi_application

from filemaster.tasks import *
from filemaster.models import *

import logging
log = logging.getLogger(__name__)

application = get_wsgi_application()
User = get_user_model()
today = date.today()
daysago = today - timedelta(days=10)

for af in ArchiveFile.objects.filter(expirationdate__gt=daysago,expirationdate__lt=today):
    copysuccessful = False
    try:
        if (af.locations.all()[0].url.startswith("s3://") or af.locations.all()[0].url.startswith("S3://")) and af.locations.all()[0].storagetype!="glacier":
            bucket,path = af.locations.all()[0].get_bucket()
            if bucket and settings.BUCKETS[bucket]["glaciertype"]=="vault":
                glacierVaultMove.delay(af.locations.all()[0].url,af.id)
    except Exception as e:
        log.error(e)
