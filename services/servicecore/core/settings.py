import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-key')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'corsheaders',  # Deshabilitado: CORS manejado por nginx
    'rest_framework',
    'drf_spectacular',
    'api',  # Core API app
    'catalog',
    'transc',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'corsheaders.middleware.CorsMiddleware',  # Deshabilitado: CORS manejado por nginx
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'core.wsgi.application'

DB_ENGINE = os.environ.get("CORE_DB_ENGINE", "postgresql").lower()

postgresql_config = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("CORE_DB_NAME", "core_db"),
    "USER": os.environ.get("CORE_DB_USER", "core_user"),
    "PASSWORD": os.environ.get("CORE_DB_PASSWORD", "core_pass"),
    "HOST": os.environ.get("CORE_DB_HOST", "core_db"),
    "PORT": os.environ.get("CORE_DB_PORT", "5432"),
}

if DB_ENGINE == "postgresql":
    DATABASES = {
        "default": postgresql_config,
        "postgresql_db": postgresql_config.copy(),
        "mongodb": {
            "ENGINE": "django.db.backends.dummy",
            "NAME": os.environ.get("MONGO_DB_NAME", "core_db"),
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
        "postgresql_db": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
        "mongodb": {
            "ENGINE": "django.db.backends.dummy",
            "NAME": os.environ.get("MONGO_DB_NAME", "core_db"),
        },
    }

DATABASE_ROUTERS = ['core.db_routers.ServiceCoreRouter']

MONGODB_SETTINGS = {
    "HOST": os.environ.get("MONGO_HOST", "mongodb"),
    "PORT": int(os.environ.get("MONGO_PORT", "27017")),
    "USERNAME": os.environ.get("MONGO_ROOT_USERNAME", ""),
    "PASSWORD": os.environ.get("MONGO_ROOT_PASSWORD", ""),
    "NAME": os.environ.get("MONGO_DB_NAME", "core_db"),
    "AUTH_SOURCE": os.environ.get("MONGO_AUTH_SOURCE", "admin"),
    "PRODUCT_COLLECTION": os.environ.get("MONGO_PRODUCT_COLLECTION", "products"),
    "CATALOG_COLLECTION": os.environ.get("MONGO_CATALOG_COLLECTION", "catalogs"),
}

INTERNAL_SYNC_TOKEN = os.environ.get("INTERNAL_SYNC_TOKEN", "")

ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY", "")
ODOO_PRODUCT_MODEL = os.environ.get("ODOO_PRODUCT_MODEL", "product.template")
ODOO_SKU_FIELD = os.environ.get("ODOO_SKU_FIELD", "default_code")
ODOO_PRICE_FIELD = os.environ.get("ODOO_PRICE_FIELD", "list_price")
ODOO_STOCK_FIELD = os.environ.get("ODOO_STOCK_FIELD", "qty_available")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Core Service API',
    'DESCRIPTION': 'API documentation for core microservice',
    'VERSION': '1.0.0',
    'SERVERS': [
        {
            'url': '/core/api/v1',
            'description': 'Gateway base URL',
        }
    ],
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
    'SECURITY': [{'BearerAuth': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
    },
}

# ── CORS Configuration ────────────────────────────────────────────────
# NOTA: CORS está manejado por nginx gateway, no por Django
# Las siguientes configuraciones están deshabilitadas para evitar headers duplicados
# _default_cors_origin_re = r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'
# _cors_raw = os.environ.get('CORS_ALLOWED_ORIGIN_REGEXES', _default_cors_origin_re).strip()
# CORS_ALLOWED_ORIGIN_REGEXES = (
#     [p.strip() for p in _cors_raw.split(',') if p.strip()]
#     if _cors_raw
#     else [_default_cors_origin_re]
# )
# CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_HEADERS = (
#     'accept',
#     'accept-encoding',
#     'authorization',
#     'content-type',
#     'dnt',
#     'origin',
#     'user-agent',
#     'x-csrftoken',
#     'x-requested-with',
#     'x-api-key',
#     'x-origin',
# )
