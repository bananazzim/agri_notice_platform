"""
Production settings for agri_notice_platform.

Extends base settings with production-specific configurations.
"""
from .base import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Allowed hosts - must be set via environment variable
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Security settings (strict for production)
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
SECURE_BROWSER_XSS_FILTER = True

# HSTS settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security Policy
SECURE_CONTENT_SECURITY_POLICY = {
    'BASE_URI': ("'self'",),
    'DEFAULT_SRC': ("'self'",),
    'SCRIPT_SRC': ("'self'", "cdn.jsdelivr.net"),
    'STYLE_SRC': ("'self'", "cdn.jsdelivr.net", "'unsafe-inline'"),
    'IMG_SRC': ("'self'", "data:", "https:"),
    'FONT_SRC': ("'self'", "cdn.jsdelivr.net"),
}

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# Cache settings (Redis for production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'KEY_PREFIX': 'agri_notice_platform',
        'TIMEOUT': 300,
    }
}

# Session cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Database - PostgreSQL
DATABASES['default']['CONN_MAX_AGE'] = 600

# Logging (production level)
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['crawlers']['level'] = 'INFO'
LOGGING['loggers']['scheduler']['level'] = 'INFO'

# Disable debug toolbar
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

if 'debug_toolbar.middleware.DebugToolbarMiddleware' in MIDDLEWARE:
    MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')

# Static files compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CORS - restricted for production
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
