from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Use SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use Local Memory Cache instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Configure Celery to run synchronously
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable Rate Limiting (or it will use LocMemCache which might work)
RATELIMIT_ENABLE = False

# Email to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
