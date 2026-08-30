"""
Test settings for the Classic Models API tests.
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-test-key-for-testing-only"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    # Local apps
    "classicmodels",
    "authentication",
    "events",
    "api.v1",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# Use SQLite for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "authentication.api_key_auth.ApiKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # Disable throttling for tests to avoid rate limit failures
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# Enable API key auth tests
os.environ.setdefault("API_KEY", "test-api-key-12345")

# JWT Configuration
JWT_ISSUER = "https://classic-models.test/issuer"
JWT_AUDIENCE = "classic-models-api"
JWT_KEY_ID = "test-key-1"
JWT_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDP2B+0CX+vtS0G
qJybQVK5WrW6G86LUAmVp+ftdXkSc0UwJDwTimEDuu1pIrOJHgvvuCzaiLR7HQvV
OtTNDp4EC9ZSPLTLc6V+ncNKHNA7AWW3kU1dpmlAsbxZJdWcjRdL6XLSpOinKeDV
QJMAfmVtyf5HMtEKhirUEd8pHu3APWM9ZgQlot44+3kWzAP1Rk23O89IyBuzQnGa
e9sLSGuGH9VjyZCmb6+O21iS9YPOijDZklHVg6A6ksrhYoJSpPjZFrhCwkfMXG2Z
6vqHbJ5UkXZtWokTbgUx0BHtvyJFJog42SpEV1qk6DNL5kbsweaCIZ/hQxu0Dby6
zMu7yPEXAgMBAAECggEARZcQbmBrzzHzRHJ6FQWXJBZ6GDktO7ntq50Pa5NUmVfd
B5RqRQSlHPGeggArarKTvozE/9qby0jbaGaNT6cgQyyPcvN+eUxcUfuSoqLpGYiL
PR46cCvCu/WGobaoQgV/klw0pNCwUSAVdnFrhtPLNCpYqBAcq9BmUKE3PfZsFlwc
gTonYab+kmKX9xPrvPKVmv3IloWVKCkGKcXLfWNfpIm0A7S1fnmDRZIm/D7vHD8K
oiA5w6VFXYZgrlLz6LJyhfOx6Ml8/AzzoeNMljIsP57v14r0qZf+NRK1dKIfwaUq
kqB38SKyVrEr3VRk23T7lBuGoBJGoZRIT6+fpPTp2QKBgQD6B4BnoDxNO1bOKXFy
0awcIgNpf+qsmCLhtPJSYa2+5A0XHrQuyDWk+g/QnPHIEoeTmrxFBB34YMz171Qg
kkEAg8+p6upmyxYPWX4TBZeMZ3BWMZfjmLwEExKLBMTUB4s8CZ7MaAJojVJDlzjn
Uv4kjMtmUCkDusHnMzlfmJ5kywKBgQDUzru1pze7618VhFgYhQyx36kIIiK/vJwx
SG93tXWEEcPe4ocDNwJoBJpKpf6Plf+p+8E/9EGnBlSa610j6TgrzSwthbYwP/XQ
ZkLORDxKdA0ltg1Jb2T44fhVBQ1vLZnZMHbT9FuIIbHWGnoVvb8OO8RNYaG4otkJ
P3ojFgjnZQKBgEY0iQeP5J7DBLLKzEIzQaJ8onyjIF/qMBE0X75mEwVAv7Q4ONvR
984lMP+gsfs9yLfXgPnYGBpABA0icHrc1kewu0S446yNZdpVhKMOtOkFunNZZY7Q
uipiuJg0dJgcrinjgaVfpx14YRr9gUri8N2OcyZ9Z6bWb8/dgESpdABVAoGARK1L
Cr6iT/UPxIPnYlJd3HGPvV421KXrykPUJU/cUvjgu2djpvfzwNnraTfUxUXlMlha
72bGYT67wxs9/b7gL9KQ9Uf3me6qR80YtjRzOJvnOkpcU1ytu1xBpj5xLXYL9nmb
f5+WgoJNQAlfaPDJXbCQE2D0rf9wB3oC0pvj17kCgYEA3z+jh5zwsHJpkzg3lGTX
2XzmZKuJFs307khp44ILct4kNK074JtCUaYbExMlo5pCodZL5w8rDmz2ZZBpR4qN
fzpGCVu+Ng+I0bEk/3Iy/ZYBXVdQFt6j5YAh1+nolOm4VLuDHWoCc9CwrHAr5Wz7
uhOgHUkMCho7H5vzHf0qTNQ=
-----END PRIVATE KEY-----"""
JWT_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAz9gftAl/r7UtBqicm0FS
uVq1uhvOi1AJlafn7XV5EnNFMCQ8E4phA7rtaSKziR4L77gs2oi0ex0L1TrUzQ6e
BAvWUjy0y3Olfp3DShzQOwFlt5FNXaZpQLG8WSXVnI0XS+ly0qTopyng1UCTAH5l
bcn+RzLRCoYq1BHfKR7twD1jPWYEJaLeOPt5FswD9UZNtzvPSMgbs0JxmnvbC0hr
hh/VY8mQpm+vjttYkvWDzoow2ZJR1YOgOpLK4WKCUqT42Ra4QsJHzFxtmer6h2ye
VJF2bVqJE24FMdAR7b8iRSaIONkqRFdapOgzS+ZG7MHmgiGf4UMbtA28uszLu8jx
FwIDAQAB
-----END PUBLIC KEY-----"""

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "RS256",
    "SIGNING_KEY": JWT_PRIVATE_KEY_PEM,
    "VERIFYING_KEY": JWT_PUBLIC_KEY_PEM,
    "AUDIENCE": JWT_AUDIENCE,
    "ISSUER": JWT_ISSUER,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("authentication.jwt_tokens.CustomAccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Classic Models API",
    "DESCRIPTION": "API for Classic Models database",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
}

# Logging configuration for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "classicmodels": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Test-specific settings
TEST_RUNNER = "django.test.runner.DiscoverRunner"


# Disable migrations for tests to speed them up
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Cache configuration for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Security settings for tests
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
X_FRAME_OPTIONS = "DENY"

# Session configuration for tests
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production
SESSION_SAVE_EVERY_REQUEST = False

# CSRF configuration for tests
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  # Set to True in production
CSRF_TRUSTED_ORIGINS: list[str] = []

# File upload settings for tests
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Internationalization settings for tests
USE_L10N = True
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ","
DECIMAL_SEPARATOR = "."
NUMBER_GROUPING = 3

# Time zone settings for tests
USE_TZ = True

# Static files settings for tests
STATICFILES_DIRS: list[str] = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Media files settings for tests
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Test database settings
if "test" in os.environ.get("DJANGO_SETTINGS_MODULE", ""):
    # Use in-memory SQLite for faster tests
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {  # type: ignore[dict-item]
            "timeout": 20,
        },
    }

    # Disable migrations for tests
    MIGRATION_MODULES = DisableMigrations()

    # Use faster password hashing for tests
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    # Disable logging during tests
    handlers = LOGGING.get("handlers", {})
    if handlers and hasattr(handlers, "__contains__") and "console" in handlers:
        handlers["console"]["level"] = "CRITICAL"  # type: ignore[index]
    loggers = LOGGING.get("loggers", {})
    if loggers:
        for logger in loggers.values():  # type: ignore[attr-defined]
            logger["level"] = "CRITICAL"
