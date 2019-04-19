from fileservice.settings import *

# Override databases setting to use sqlite3 during testing.
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}

# Increase logging levels so the boto3 logs are surpressed when running tests.
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
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'stream': sys.stdout,
        }
    },
    'root': {
        'handlers': ['console', 'sentry', ],
        'level': 'ERROR',
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
    },
}