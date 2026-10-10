import secrets
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
env_file = BASE_DIR / '.env'
if env_file.is_file():
    environ.Env.read_env(env_file, overwrite=False)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEBUG = env.bool('DJANGO_DEBUG', default=True)
SECRET_KEY = env('DJANGO_SECRET_KEY', default='')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DEBUG is False.')
    SECRET_KEY = secrets.token_urlsafe(50)

ALLOWED_HOSTS = env.list(
    'DJANGO_ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', '[::1]'],
)

CSRF_TRUSTED_ORIGINS = env.list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    default=['http://127.0.0.1:5173', 'http://localhost:5173'] if DEBUG else [],
)
SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=not DEBUG)
SECURE_HSTS_SECONDS = env.int(
    'DJANGO_SECURE_HSTS_SECONDS',
    default=0 if DEBUG else 31536000,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS',
    default=False,
)
SECURE_HSTS_PRELOAD = env.bool('DJANGO_SECURE_HSTS_PRELOAD', default=False)
SECURE_PROXY_SSL_HEADER = (
    ('HTTP_X_FORWARDED_PROTO', 'https')
    if env.bool('DJANGO_TRUST_PROXY_SSL_HEADER', default=False)
    else None
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'drf_spectacular',
    'accounts.apps.AccountsConfig',
    'properties.apps.PropertiesConfig',
    'favorites.apps.FavoritesConfig',
    'viewings.apps.ViewingsConfig',
    'user.apps.UserConfig',
    'admin.apps.AdminConfig',
    'owner_announcements.apps.OwnerAnnouncementsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'accounts.middleware.LocalInvitationCsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.OwnerOnlyDjangoAdminMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'house.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'house.wsgi.application'

database_url = env('DATABASE_URL', default='')
if database_url:
    database_config = env.db_url_config(database_url)
    if database_config['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('DATABASE_URL must use PostgreSQL.')
    DATABASES = {
        'default': {
            **database_config,
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'TEST': {
                'NAME': env('POSTGRES_TEST_DB', default=None),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('POSTGRES_DB'),
            'USER': env('POSTGRES_USER'),
            'PASSWORD': env('POSTGRES_PASSWORD'),
            'HOST': env('POSTGRES_HOST', default='localhost'),
            'PORT': env('POSTGRES_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'TEST': {
                'NAME': env('POSTGRES_TEST_DB', default=None),
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_TZ = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'frontend' / 'node_modules' / 'leaflet' / 'dist',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'house.api_pagination.StandardResultsSetPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'house.api_errors.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'account_login': '10/minute',
        'account_registration': '5/hour',
        'public_viewing_request': '10/hour',
        'public_viewing_receipt': '20/hour',
        'public_listing_report': '5/hour',
        'delegated_invitation_accept': '10/hour',
    },
}

if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'habesha-homes-development',
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache',
        },
    }

SPECTACULAR_SETTINGS = {
    'TITLE': 'Addis Ababa Property Marketplace API',
    'DESCRIPTION': 'Versioned API for verified property listings and viewing requests.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
