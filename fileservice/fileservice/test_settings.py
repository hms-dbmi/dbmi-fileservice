from fileservice.settings import *

# Override databases setting to use sqlite3 during testing.
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}
