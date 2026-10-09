"""Minimal production-capable Django configuration for SireSoft-IKON."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEBUG = os.getenv('SIREIKON_DEBUG', '0') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-change-this-before-deploying-siresoft-ikon'
    else:
        # No fixed insecure hard-coded secret in production. For convenience,
        # allow check/manage.py with no secret; production must set the env.
        raise RuntimeError('Set DJANGO_SECRET_KEY for SireSoft-IKON production Django')
ALLOWED_HOSTS = [v.strip() for v in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if v.strip()]
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if v.strip()]
ROOT_URLCONF = 'ikon_django.urls'
INSTALLED_APPS = ['django.contrib.staticfiles']
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = []
WSGI_APPLICATION = 'ikon_django.wsgi.application'
ASGI_APPLICATION = 'ikon_django.asgi.application'
DATABASES = {
    'default': {
        'ENGINE': os.getenv('SIREIKON_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('SIREIKON_DB_NAME', str(BASE_DIR / 'ikon.sqlite3')),
    }
}
if DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default'].update({
        'USER': os.getenv('SIREIKON_DB_USER', ''),
        'PASSWORD': os.getenv('SIREIKON_DB_PASSWORD', ''),
        'HOST': os.getenv('SIREIKON_DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('SIREIKON_DB_PORT', ''),
    })
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
