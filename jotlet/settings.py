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
import sys
from datetime import timedelta
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

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

TESTING = (sys.argv[1:2] == ["test"]) or ("pytest" in sys.modules)
DEBUG = TESTING if TESTING else env("DEBUG", default=False)
DEBUG_TOOLBAR_ENABLED = env("DEBUG_TOOLBAR_ENABLED", default=False)

if not DEBUG and env("SENTRY_ENABLED", default=False):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=env("SENTRY_DSN"),
        integrations=[
            DjangoIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=env("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST", default=False)
if USE_X_FORWARDED_HOST:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SITE_ID = 1

INSTALLED_APPS = []
if DEBUG:
    INSTALLED_APPS += ["whitenoise.runserver_nostatic"]

# Application definition
INSTALLED_APPS += [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "axes",
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
    "mptt",
    "accounts",
    "boards",
    "django_cleanup.apps.CleanupConfig",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
    "axes.middleware.AxesMiddleware",
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
            os.path.join(BASE_DIR / "jotlet" / "templates"),
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
                "jotlet.context_processors.hcaptcha_sitekey",
            ],
        },
    },
]

ASGI_APPLICATION = "jotlet.asgi.application"

if not TESTING:
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
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "jotlet",
            "USER": os.environ.get("DB_USER", "vscode"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "notsecure"),
            "HOST": os.environ.get("DB_HOST", "postgres"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

CONN_MAX_AGE = env("CONN_MAX_AGE", default=60)

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

Q_CLUSTER = {
    "name": "DjangORM",
    "sync": TESTING,
    "workers": 2,
    "timeout": 1800,
    "retry": 1800,
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
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AXES_ENABLED = not TESTING
AXES_USERNAME_FORM_FIELD = "login"
AXES_FAILURE_LIMIT = env("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = timedelta(minutes=env("AXES_COOLOFF_MINUTES", default=15))
AXES_LOCKOUT_URL = "/accounts/lockout/"
AXES_PROXY_COUNT = env("AXES_PROXY_COUNT", default=0)

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
    AWS_S3_SIGNATURE_VERSION = "s3v4"
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
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if TESTING
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STATICFILES_DIRS = [os.path.join(BASE_DIR, "jotlet", "static")]

if not TESTING:
    REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")
    REDIS_UNIX_SOCKET = env("REDIS_UNIX_SOCKET", default=False)
    if not REDIS_UNIX_SOCKET:
        REDIS_HOST = env("REDIS_HOST", default=("localhost"))
        REDIS_PORT = env("REDIS_PORT", default=6379)

    CACHES = {
        "default": {
            "BACKEND": env("REDIS_BACKEND", default="django_redis.cache.RedisCache"),
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "jotlet",
            "OPTIONS": {
                "parser_class": "redis.connection.HiredisParser",
            },
        }
    }

    CACHEOPS_REDIS = REDIS_URL

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    {
                        "address": (REDIS_HOST, REDIS_PORT) if not REDIS_UNIX_SOCKET else REDIS_URL,
                    }
                ],
                "prefix": "jotlet",
                "capacity": 500,
                "symmetric_encryption_keys": [SECRET_KEY],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "KEY_PREFIX": "jotlet",
        }
    }

CACHALOT_ENABLED = False if TESTING else env("CACHALOT_ENABLED", default=True)
CACHALOT_TIMEOUT = env("CACHALOT_TIMEOUT", default=31556952)
CACHALOT_UNCACHABLE_APPS = frozenset(
    (
        "axes",
        "simple_history",
    )
)
CACHALOT_UNCACHABLE_TABLES = frozenset(
    (
        "django_migrations",
        "boards_post",
        "boards_reaction",
    )
)

CACHEOPS_ENABLED = False if TESTING else env("CACHEOPS_ENABLED", default=True)
CACHEOPS_DEFAULTS = {"timeout": env("CACHEOPS_TIMEOUT", default=31556952)}
CACHEOPS = {
    "boards.post": {"ops": "all"},
    "boards.reaction": {"ops": "all"},
    "*.*": {"ops": ()},
}
CACHEOPS_LRU = env("CACHEOPS_LRU", default=True)

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

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if TESTING
    else env("EMAIL_BACKEND", default="django_q_email.backends.DjangoQBackend")
)
DJANGO_Q_EMAIL_BACKEND = env("DJANGO_Q_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
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

HCAPTCHA_ENABLED = True if TESTING else env("HCAPTCHA_ENABLED", default=False)
if HCAPTCHA_ENABLED:
    HCAPTCHA_VERIFY_URL = env("VERIFY_URL", default="https://hcaptcha.com/siteverify")
    if not TESTING:
        HCAPTCHA_SITE_KEY = env("HCAPTCHA_SITE_KEY")
        HCAPTCHA_SECRET_KEY = env("HCAPTCHA_SECRET_KEY")
    else:
        HCAPTCHA_SITE_KEY = "10000000-ffff-ffff-ffff-000000000001"
        HCAPTCHA_SECRET_KEY = "0x0000000000000000000000000000000000000000"

CSP_DEFAULT_SRC = ["'none'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "polyfill.io",
    "unpkg.com",
    "'unsafe-eval'",
] + env.list("CSP_SCRIPT_SRC", default=[])
CSP_STYLE_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "maxcdn.bootstrapcdn.com",
    "'unsafe-inline'",
] + env.list("CSP_STYLE_SRC", default=[])
CSP_FONT_SRC = CSP_STYLE_SRC + env.list("CSP_FONT_SRC", default=[])
CSP_IMG_SRC = [
    "'self'",
    "data:",
] + env.list("CSP_IMG_SRC", default=[])
CSP_BASE_URI = ["'none'"] + env.list("CSP_BASE_URI", default=[])
CSP_CONNECT_SRC = [
    "'self'",
    "maxcdn.bootstrapcdn.com",
] + env.list("CSP_CONNECT_SRC", default=[])
CSP_FRAME_SRC = env.list("CSP_FRAME_SRC", default=[])
CSP_INCLUDE_NONCE_IN = ["script-src"] + env.list("CSP_INCLUDE_NONCE_IN", default=[])

if HCAPTCHA_ENABLED:
    CSP_SCRIPT_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_STYLE_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_CONNECT_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_FRAME_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
