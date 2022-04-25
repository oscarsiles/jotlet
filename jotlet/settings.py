"""
Django settings for jotlet project. 
Use a .env file to store configuration variables.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import mimetypes
import os
from pathlib import Path

import environ
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

mimetypes.add_type("text/javascript", ".js", True)

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG", default=False)
DEBUG_TOOLBAR_ENABLED = env("DEBUG_TOOLBAR_ENABLED", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST", default=False)
if USE_X_FORWARDED_HOST:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SITE_ID = 1

# Application definition
INSTALLED_APPS = [
    "jazzmin",
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.microsoft",
    "crispy_forms",
    "crispy_bootstrap5",
    "channels",
    "django_htmx",
    "django_q",
    "django_filters",
    "qr_code",
    "sorl.thumbnail",
    "simple_history",
    "cachalot",
    "cacheops",
    "accounts",
    "boards",
    "django_cleanup.apps.CleanupConfig",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "csp.middleware.CSPMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

if DEBUG_TOOLBAR_ENABLED and DEBUG:
    RENDER_PANELS = False
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

ROOT_URLCONF = "jotlet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [
            os.path.join(BASE_DIR / "templates"),
            os.path.join(BASE_DIR / "accounts" / "templates" / "allauth"),
        ],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "csp.context_processors.nonce",
            ],
        },
    },
]

ASGI_APPLICATION = "jotlet.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="jotlet"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default=""),
        "PORT": env("DB_PORT", default=""),
    }
}

CONN_MAX_AGE = env("CONN_MAX_AGE", default=60)

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

Q_CLUSTER = {
    "name": "DjangORM",
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "catch_up": False,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

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

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Europe/London")
USE_I18N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "boards:index"
LOGOUT_REDIRECT_URL = "boards:index"

USE_S3 = env("USE_S3", default=False)
if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN")
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=2592000"}
    AWS_IS_GZIPPED = False
    # s3 public media settings
    THUMBNAIL_FORCE_OVERWRITE = True
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "jotlet.storage_backends.PublicMediaStorage"
else:
    MEDIA_URL = "media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")
REDIS_UNIX_SOCKET = env("REDIS_UNIX_SOCKET", default=False)
if not REDIS_UNIX_SOCKET:
    REDIS_HOST = env("REDIS_HOST", default=("localhost"))
    REDIS_PORT = env("REDIS_PORT", default=6379)

CACHES = {
    "default": {
        "BACKEND": env("REDIS_BACKEND", default="django.core.cache.backends.redis.RedisCache"),
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "jotlet",
        "OPTIONS": {
            "PARSER_CLASS": "redis.connection.HiredisParser",
        },
    }
}

CACHEOPS_REDIS = {
    **(
        {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
        }
        if not REDIS_UNIX_SOCKET
        else {
            "unix_socket_path": REDIS_URL,
        }
    ),
    "db": 1,
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                {
                    "address": (REDIS_HOST, REDIS_PORT) if not REDIS_UNIX_SOCKET else REDIS_URL,
                    "db": 2,
                }
            ],
            "prefix": "jotlet",
            "capacity": 500,
            "symmetric_encryption_keys": [SECRET_KEY],
        },
    },
}

CACHALOT_ENABLED = env("CACHALOT_ENABLED", default=True)
CACHEOPS_ENABLED = env("CACHEOPS_ENABLED", default=True)

CACHALOT_UNCACHABLE_APPS = frozenset(("simple_history",))
CACHALOT_UNCACHABLE_TABLES = frozenset(
    (
        "django_migrations",
        "boards_post",
        "boards_reaction",
    )
)

CACHEOPS_DEFAULTS = {"timeout": 60 * 60}
CACHEOPS = {
    "boards.post": {"ops": "all"},
    "boards.reaction": {"ops": "all"},
    "*.*": {"ops": ()},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {pathname}: {message}",
            "style": "{",
        },
    },
    "handlers": {"console": {"level": "WARNING", "class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "jotlet": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_FAIL_SILENTLY = not DEBUG

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="")


ACCOUNT_ADAPTER = "accounts.adapter.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomSocialAccountAdapter"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_MAX_EMAIL_ADDRESSES = 1
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_ALLOW_SIGNUPS = True

SOCIALACCOUNT_ALLOW_SIGNUPS = ACCOUNT_ALLOW_SIGNUPS
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_EMAIL_VERIFICATION = ACCOUNT_EMAIL_VERIFICATION

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "offline",
        },
    }
}

CSP_DEFAULT_SRC = ["'none'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "polyfill.io",
    "unpkg.com",
    "'unsafe-eval'",
]
CSP_STYLE_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "'unsafe-inline'",
]
CSP_FONT_SRC = CSP_STYLE_SRC
CSP_IMG_SRC = [
    "'self'",
    "data:",
]
CSP_BASE_URI = ["'none'"]
CSP_CONNECT_SRC = ["'self'"]
CSP_INCLUDE_NONCE_IN = ["script-src"]
