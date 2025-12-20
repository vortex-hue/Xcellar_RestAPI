from .base import *

DEBUG = False

# CRITICAL: Immediately remove debug_toolbar before anything else can use it
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']

# CRITICAL: Redefine MIDDLEWARE immediately to ensure debug_toolbar is never included
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'xcellar.middleware.ProxyMiddleware',  # Add ProxyMiddleware here
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Trust the X-Forwarded-Proto header for SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Database
db_ssl_mode = os.environ.get('DB_SSLMODE', os.environ.get('DB_SSL_MODE', 'require'))
db_options = {}
if db_ssl_mode and db_ssl_mode != 'disable':
    db_options['sslmode'] = db_ssl_mode

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': db_options,
    }
}

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Exclude debug_toolbar from static files collection
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


