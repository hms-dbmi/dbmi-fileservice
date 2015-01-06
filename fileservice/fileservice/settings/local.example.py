"""Development settings and globals."""

from __future__ import absolute_import

from os.path import join, normpath

from .base import *


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': normpath(join(DJANGO_ROOT, 'default.db')),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## TOOLBAR CONFIGURATION
# See: http://django-debug-toolbar.readthedocs.org/en/latest/installation.html#explicit-setup
INSTALLED_APPS += (
    'debug_toolbar',
)

MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_PATCH_SETTINGS = False

# http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
INTERNAL_IPS = ('127.0.0.1',)
########## END TOOLBAR CONFIGURATION
ENCRYPTED_FIELDS_KEYDIR = '/opt/kz'

##AUTH0
AUTH0_CLIENT_ID="x"
AUTH0_CLIENT_SECRET="x" 
AUTH0_DOMAIN="hms-dbmi.auth0.com"
AUTH0_CALLBACK_URL="http://localhost:8000/callback/"
S3_ID="x"
S3_SECRET="x"
S3_UPLOAD_BUCKET="udnarchive-ci"

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'haystack',
    },
}
HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False

# increase the default number of results (from 20)
HAYSTACK_SEARCH_RESULTS_PER_PAGE = 40
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
#HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

BUCKETS = {
           S3_UPLOAD_BUCKET:{
                             "type":"s3",
                             "AWS_KEY_ID":"AAAAAXXX",
                             "AWS_SECRET":"AAAAAXXX"
                             } 
           }