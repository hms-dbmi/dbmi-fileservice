from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging

logger = logging.getLogger(__name__)


def add_view_permissions(sender, **kwargs):
    """
    This syncdb hooks takes care of adding a view permission too all our
    content types.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission

    # for each of our content types
    logger.debug('post-migrate: Checking configured view permissions')
    for content_type in ContentType.objects.all():
        # build our permission slug
        codename = "view_%s" % content_type.model

        # if it doesn't exist..
        if not Permission.objects.filter(content_type=content_type, codename=codename):
            # add it
            Permission.objects.create(content_type=content_type,
                                      codename=codename,
                                      name="Can view %s" % content_type.name)
            logger.info("post-migrate: Added view permission for %s" % content_type.name)


def buckets(sender, **kwargs):
    """
    Ensures Bucket table reflects the S3 buckets that have been configured for this instance
    """
    from django.conf import settings
    from filemaster.models import Bucket

    # Iterate buckets
    logger.debug('post-migrate: Checking configured AWS buckets for entry in Bucket table')
    for bucket in settings.BUCKETS:
        bucket, created = Bucket.objects.get_or_create(name=bucket)
        if created:
            logger.info('post-migrate: Added Bucket \'{}\''.format(bucket))


class FilemasterConfig(AppConfig):
    name = 'filemaster'
    verbose_name = "Filemaster"

    def ready(self):
        """
        Run any one-time only startup routines here
        """
        # Check Buckets after migrations are run
        post_migrate.connect(buckets, sender=self)

        # check for all our view permissions after a syncdb
        post_migrate.connect(add_view_permissions, sender=self)

