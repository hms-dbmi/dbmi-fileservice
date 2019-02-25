"""Common settings and globals."""


from os.path import abspath, basename, dirname, join, normpath
from sys import path
import os, sys
from django.utils.crypto import get_random_string

from dbmi_client import environment

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(abspath(__file__))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = ()

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': environment.get_str('MYSQL_NAME', 'fileservice'),
        'USER': environment.get_str('MYSQL_USER', 'fileservice'),
        'PASSWORD': environment.get_str('MYSQL_PASSWORD'),
        'HOST': environment.get_str('MYSQL_HOST'),
        'PORT': environment.get_str('MYSQL_PORT', '3306'),
    }
}
########## END DATABASE CONFIGURATION

########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'America/New_York'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = environment.get_str("SECRET_KEY", get_random_string(50, chars))
########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = environment.get_list("ALLOWED_HOSTS")
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(SITE_ROOT, 'templates'))],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'dbmi_client.middleware.DBMIJWTAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
)

# Apps specific for this project go here.
LOCAL_APPS = (
    'guardian',
    'rest_framework',
    'rest_framework.authtoken',
    'filemaster',
    'bootstrap3',
    'taggit',
    'taggit_serializer',
    'django_nose',
    'axes',
    'health_check',
    'health_check.db',
    'dbmi_client',
    'dbmi_client.login',
)

# Fixes duplicate errors in MYSQL
TAGGIT_CASE_INSENSITIVE = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS
########## END APP CONFIGURATION


######## AUTH CONFIG
AUTHENTICATION_BACKENDS = (
    'dbmi_client.authn.DBMIUsersModelAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# Custom user model
AUTH_USER_MODEL = 'filemaster.CustomUser'

# Guardian user settings
GUARDIAN_GET_INIT_ANONYMOUS_USER = 'filemaster.models.get_anonymous_user_instance'
ANONYMOUS_USER_ID = 1
##### END AUTH CONFIG


######## DBMI CLIENT CONFIG
DBMI_CLIENT_CONFIG = {
    'CLIENT': 'dbmifileservice',

    # Auth0 account details
    'AUTH0_CLIENT_ID': environment.get_str('DBMI_AUTH0_CLIENT_ID'),
    'AUTH0_SECRET': environment.get_str('DBMI_AUTH0_SECRET'),
    'AUTH0_TENANT': environment.get_str('DBMI_AUTH0_TENANT'),
    'JWT_AUTHZ_NAMESPACE': environment.get_str('DBMI_JWT_AUTHZ_NAMESPACE'),

    # Optionally disable logging
    'ENABLE_LOGGING': True,

    # Universal login screen branding
    'AUTHN_TITLE': 'DBMI Fileservice',
    'AUTHN_ICON_URL': None,

    # AuthZ groups/roles/permissions
    'AUTHZ_ADMIN_GROUP': 'DBMI',
    'AUTHZ_ADMIN_PERMISSION': 'ADMIN',

    # Login redirect
    'LOGIN_REDIRECT_URL': environment.get_str('DBMI_LOGIN_REDIRECT_URL'),

    # JWT bits
    'JWT_COOKIE_DOMAIN': environment.get_str('DBMI_JWT_COOKIE_DOMAIN'),

    # Autocreate users
    'USER_MODEL_AUTOCREATE': True,
}
######## END DBMI CLIENT CONFIG


######## DJANGO REST FRAMEWORK CONFIG
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.YAMLRenderer'
    )
}
######## END DJANGO REST FRAMEWORK CONFIG


########## AWS S3 CONFIGURATION

# Set the default S3 bucket to use when not specified
S3_DEFAULT_BUCKET = os.environ.get('AWS_S3_UPLOAD_BUCKET')
AWS_STS_ACCESS_KEY_ID = os.environ.get('AWS_STS_ACCESS_KEY_ID')
AWS_STS_SECRET_ACCESS_KEY = os.environ.get('AWS_STS_SECRET_ACCESS_KEY')

BUCKETS = {
    S3_DEFAULT_BUCKET: {
        'type': 's3',
        'glaciertype': 'lifecycle',
        'AWS_KEY_ID': AWS_STS_ACCESS_KEY_ID,
        'AWS_SECRET': AWS_STS_SECRET_ACCESS_KEY
    }
}

# Include all additional buckets and AWS credentials like follows:
# Bucket specification format:
# <S3 bucket name>: {
#   "AWS_KEY_ID": <AWS STS key id>,
#   "AWS_SECRET": <AWS STS secret key>
# },
BUCKETS.update({
    bucket: {
        'type': 's3',
        'glaciertype': 'lifecycle',
        'AWS_KEY_ID': credentials.get('AWS_KEY_ID'),
        'AWS_SECRET': credentials.get('AWS_SECRET'),
    } for bucket, credentials in environment.get_dict('AWS_S3_BUCKETS').items()
})

# Add glacier
BUCKETS["Glacier"] = {"type": "glacier"}

########## END AWS S3 CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
# Configure logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[%(asctime)s][%(levelname)s][%(name)s.%(funcName)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'urllib3': {
            'handlers': ['console'],
            'level': 'WARNING'
        }
    },
}
########## END LOGGING CONFIGURATION


########## TEST CONFIGURATION
TEST_AWS_KEY = environment.get_str('TEST_AWS_KEY', 'AKIAxxxxx')
TEST_AWS_SECRET = environment.get_str('TEST_AWS_SECRET', 'asdfadsfadsf')
EXPIRATIONDATE = 200
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
########## END TEST CONFIGURATION