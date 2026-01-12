from .base import *

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Security Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = ['https://xcellarrestapi-production.up.railway.app']

# Cache - Use local memory instead of Redis (since Redis is not available)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Session - Use database-backed sessions instead of cache
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Disable rate limiting (depends on Redis cache)
RATELIMIT_ENABLE = False

# Celery - Disable Redis broker/backend (Redis not available)
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

