"""Common settings and globals."""


from os.path import abspath, basename, dirname, join, normpath
from sys import path, stdout

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
DEBUG = environment.get_bool("DJANGO_DEBUG", default=False)

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
        'PASSWORD': environment.get_str('MYSQL_PASSWORD', required=True),
        'HOST': environment.get_str('MYSQL_HOST', required=True),
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
SECRET_KEY = environment.get_str("SECRET_KEY", required=True)
########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = environment.get_list("ALLOWED_HOSTS", required=True)
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
    'dbmi_client.middleware.DBMIAuthenticationMiddleware',
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
    'django_filters',
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
    'django.contrib.auth.backends.ModelBackend',
)

# Custom user model
AUTH_USER_MODEL = 'filemaster.CustomUser'

# Guardian user settings
GUARDIAN_GET_INIT_ANONYMOUS_USER = 'filemaster.models.get_anonymous_user_instance'
ANONYMOUS_USER_ID = 1
##### END AUTH CONFIG


######## DBMI CLIENT CONFIG
DBMI_CLIENT_CONFIG = {
    'CLIENT': 'dbmi',

    # Auth0 account details
    'AUTH0_CLIENT_ID': environment.get_str('DBMI_AUTH0_CLIENT_ID', required=True),
    'AUTH0_SECRET': environment.get_str('DBMI_AUTH0_SECRET'),
    'AUTH0_TENANT': environment.get_str('DBMI_AUTH0_TENANT', required=True),
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
        'dbmi_client.authn.DBMIModelUser',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.YAMLRenderer'
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}
######## END DJANGO REST FRAMEWORK CONFIG


########## AWS S3 CONFIGURATION

# Set the S3 bucket(s) to enable
BUCKETS = environment.get_list('AWS_S3_BUCKETS', default=[])
if not BUCKETS:

    # The old configuration had bucke names as keys (credentials as values that are no longer needed)
    BUCKETS += environment.get_dict('AWS_S3_BUCKETS', default={}).keys()

########## END AWS S3 CONFIGURATION


########## LOGGING CONFIGURATION

# Configure sentry
if environment.get_str('RAVEN_URL', default=None):
    RAVEN_CONFIG = {
        'dsn': environment.get_str('RAVEN_URL'),
        'site': 'fileservice',
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[DBMI-Fileservice] - [%(asctime)s][%(levelname)s]'
                      '[%(name)s.%(funcName)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',  # To capture more than ERROR, change to WARNING, INFO, etc.
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'tags': {'custom-tag': 'x'},
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'stream': stdout,
        }
    },
    'root': {
        'handlers': ['console', 'sentry', ],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', ],
            'level': 'ERROR',
            'propagate': True,
        },
        'raven': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'botocore': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
        'boto3': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
        's3transfer': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': True,
        },
    },
}
########## END LOGGING CONFIGURATION


########## TEST CONFIGURATION
TEST_AWS_KEY = environment.get_str('TEST_AWS_KEY', 'AKIAxxxxx')
TEST_AWS_SECRET = environment.get_str('TEST_AWS_SECRET', 'asdfadsfadsf')
EXPIRATIONDATE = 200
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
########## END TEST CONFIGURATION