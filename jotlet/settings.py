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
import tomli
from corsheaders.defaults import default_headers
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

TESTING = "pytest" in sys.modules

mimetypes.add_type("text/javascript", ".js", True)

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
test_env_file = os.path.join(BASE_DIR, ".env.test")
if TESTING and os.path.exists(test_env_file):
    environ.Env.read_env(test_env_file)
elif not TESTING:
    environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

# workaround for poetry packages that aren't "installed"
# https://github.com/wemake-services/wemake-python-styleguide/blob/master/docs/conf.py#L22-L37
VERSION = ""
with open(os.path.join(BASE_DIR, "pyproject.toml"), mode="rb") as pyproject:
    VERSION = tomli.load(pyproject)["tool"]["poetry"]["version"]

DEBUG = env("DEBUG", default=TESTING if TESTING else False)
DEBUG_TOOLBAR_ENABLED = env("DEBUG_TOOLBAR_ENABLED", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_HEADERS = [*list(default_headers), "link"]
CORS_EXPOSE_HEADERS = ["link"]

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST", default=False)
if USE_X_FORWARDED_HOST:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SITE_ID = 1

# Application definition
INSTALLED_APPS = [
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
    "anymail",
    "axes",
    "crispy_forms",
    "crispy_bootstrap5",
    "channels",
    "django_htmx",
    "extra_views",
    "huey.contrib.djhuey",
    "hueymail",
    "bx_django_utils",
    "huey_monitor",
    "django_filters",
    "sorl.thumbnail",
    "cacheops",
    "notices",
    "accounts",
    "boards",
    "maintenance",
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
    "csp.middleware.CSPMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "notices.middleware.NoticesMiddleware",
    "axes.middleware.AxesMiddleware",
]

if DEBUG:
    INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]

    if DEBUG_TOOLBAR_ENABLED:
        import socket

        from debug_toolbar import settings as debug_toolbar_settings

        RENDER_PANELS = False
        INSTALLED_APPS += ["debug_toolbar", "template_profiler_panel"]
        MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]
        DEBUG_TOOLBAR_PANELS = [
            *debug_toolbar_settings.PANELS_DEFAULTS,
            "template_profiler_panel.panels.template.TemplateProfilerPanel",
        ]

        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

ROOT_URLCONF = "jotlet.urls"

default_loaders = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

cached_loaders = [("django.template.loaders.cached.Loader", default_loaders)]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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
                "jotlet.context_processors.captcha_sitekeys",
            ],
            "debug": DEBUG,
            "loaders": default_loaders if DEBUG else cached_loaders,
        },
    },
]

ASGI_APPLICATION = "jotlet.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="jotlet"),
        "USER": env("DB_USER", default="jotlet"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="postgres"),
        "PORT": env("DB_PORT", default="5432"),
    }
}


CONN_MAX_AGE = env("CONN_MAX_AGE", default=None, cast=int)
CONN_HEALTH_CHECKS = CONN_MAX_AGE is None or CONN_MAX_AGE > 0  # only check if we're using persistent connections

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = env("SESSION_COOKIE_AGE", default=60 * 60 * 24 * 30)  # 30 days

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

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AXES_ENABLED = env("AXES_ENABLED", default=True)

if TESTING:
    os.environ["AXES_IPWARE_PROXY_COUNT"] = "1"
    SILENCED_SYSTEM_CHECKS = ["axes.W001"]
if AXES_ENABLED and not TESTING:
    AXES_HANDLER = env(
        "AXES_HANDLER",
        default="axes.handlers.dummy.AxesDummyHandler" if TESTING else "axes.handlers.database.AxesDatabaseHandler",
    )
    AXES_USERNAME_FORM_FIELD = "login"
    AXES_FAILURE_LIMIT = env("AXES_FAILURE_LIMIT", default=5)
    AXES_COOLOFF_TIME = timedelta(minutes=env("AXES_COOLOFF_MINUTES", default=15))
    AXES_LOCKOUT_URL = "/accounts/lockout/"
    AXES_LOCKOUT_PARAMETERS = env.list("AXES_LOCKOUT_PARAMETERS", default=["username", "ip_address"])
    AXES_IPWARE_PROXY_COUNT = env("AXES_IPWARE_PROXY_COUNT", default=None, cast=int)
    AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", *AUTHENTICATION_BACKENDS]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

USE_I18N = False
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")

USE_TZ = True
TIME_ZONE = env("TIME_ZONE", default="UTC")

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
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-2")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_S3_SIGNATURE_VERSION = env("AWS_S3_SIGNATURE_VERSION", default="s3v4")
    AWS_S3_OBJECT_PARAMETERS = env("AWS_S3_OBJECT_PARAMETERS", default={"CacheControl": "max-age=2592000"})
    AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default=None)
    AWS_IS_GZIPPED = env("AWS_IS_GZIPPED", default=False)
    # s3 public media settings
    THUMBNAIL_FORCE_OVERWRITE = True
    PUBLIC_MEDIA_LOCATION = env("PUBLIC_MEDIA_LOCATION", default="media")
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
else:
    MEDIA_URL = "media/"
    if TESTING:
        import tempfile

        MEDIA_ROOT = tempfile.mkdtemp() + "/"
        WHITENOISE_AUTOREFRESH = True
    else:
        MEDIA_ROOT = os.path.join(BASE_DIR, "media")

MAX_IMAGE_WIDTH = env("MAX_IMAGE_WIDTH", default=500 if TESTING else 3840)
MAX_IMAGE_HEIGHT = env("MAX_IMAGE_HEIGHT", default=500 if TESTING else 2160)
SMALL_THUMBNAIL_WIDTH = env("SMALL_THUMBNAIL_WIDTH", default=300)
SMALL_THUMBNAIL_HEIGHT = env("SMALL_THUMBNAIL_HEIGHT", default=200)
MAX_POST_IMAGE_FILE_SIZE = env("MAX_IMAGE_FILE_SIZE", default=1024 * 1024 * 2)
MAX_POST_IMAGE_COUNT = env("MAX_POST_IMAGE_COUNT", default=100)
MAX_POST_IMAGE_WIDTH = env("MAX_POST_IMAGE_WIDTH", default=400)
MAX_POST_IMAGE_HEIGHT = env("MAX_POST_IMAGE_HEIGHT", default=MAX_POST_IMAGE_WIDTH)

THUMBNAIL_ALTERNATIVE_RESOLUTIONS = env("THUMBNAIL_ALTERNATIVE_RESOLUTIONS", default=[2])

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "jotlet", "static")]

STORAGES = {
    "default": {
        "BACKEND": "jotlet.storage_backends.PublicMediaStorage"
        if USE_S3
        else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.core.files.storage.InMemoryStorage"
        if TESTING
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
THUMBNAIL_STORAGE = STORAGES["default"]["BACKEND"]

REDIS_HOST = env("REDIS_HOST", default="localhost")
REDIS_PORT = env("REDIS_PORT", default=6379)
REDIS_URL = env("REDIS_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}")

CACHES = {
    "default": {
        "BACKEND": env("REDIS_BACKEND", default="django_redis.cache.RedisCache"),
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "jotlet_test" if TESTING else "jotlet",
        "OPTIONS": {  # type: ignore
            # this connection pool is also used for Huey
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PARSER_CLASS": "redis.connection._HiredisParser",
        },
    },
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {  # type: ignore
            "hosts": [REDIS_URL],
            "prefix": "jotlet_test" if TESTING else "jotlet",
            "capacity": 500,
        },
    },
}

CACHEOPS_ENABLED = env("CACHEOPS_ENABLED", default=True)
CACHEOPS_DEFAULTS = {"timeout": env("CACHEOPS_TIMEOUT", default=31556952)}
CACHEOPS = {
    "accounts.*": {"ops": "all", "timeout": 60 * 60 * 24},
    "auth.*": {"ops": "all", "timeout": 60 * 60 * 24},
    "axes.*": {"ops": "all", "timeout": 60 * 60 * 24},
    "boards.image": {"ops": "all"},
    "boards.bgimage": {"ops": "all"},
    "boards.postimage": {"ops": "all"},
    "boards.board": {"ops": "all"},
    "boards.boardpreferences": {"ops": "all"},
    "boards.topic": {"ops": "all"},
    "boards.post": {"ops": "all"},
    "boards.reaction": {"ops": "all"},
    "boards.additionaldata": {"ops": "all"},
    "*.*": {"ops": ()},
}
CACHEOPS_INSIDEOUT = env("CACHEOPS_INSIDEOUT", default=True)

if TESTING:
    CACHEOPS_REDIS = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": 13,
        "socket_timeout": 3,
    }
else:
    CACHEOPS_REDIS = REDIS_URL


HUEY = {
    "huey_class": "jotlet.huey.DjangoPriorityRedisExpiryHuey",  # custom class that uses django-redis pool
    "immediate": DEBUG or TESTING,
    "immediate_use_memory": False,
    "consumer": {
        "workers": env("HUEY_WORKERS", default=4, cast=int),
        "worker_type": "thread",
    },
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
CRISPY_CLASS_CONVERTERS = {
    "textinput": "inputtext textinput textInput",
    "fileinput": "fileinput fileUpload",
    "passwordinput": "textinput textInput",
}
CRISPY_FAIL_SILENTLY = not DEBUG

EMAIL_BACKEND = env("EMAIL_BACKEND", default="hueymail.backends.EmailBackend")

HUEY_EMAIL_BACKEND = env(
    "HUEY_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if TESTING
    else "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="")
FEEDBACK_EMAIL = env("FEEDBACK_EMAIL", default=None)

ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY", default=""),
    "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.eu.mailgun.net/v3"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN", default=""),
    "SENDGRID_API_KEY": env("SENDGRID_API_KEY", default=""),
}

ACCOUNT_ADAPTER = "accounts.adapter.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomSocialAccountAdapter"
ACCOUNT_EMAIL_REQUIRED = env("ACCOUNT_EMAIL_REQUIRED", default=True)
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_MAX_EMAIL_ADDRESSES = 1
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_ALLOW_SIGNUPS = env("ACCOUNT_ALLOW_SIGNUPS", default=True)

SOCIALACCOUNT_ALLOW_SIGNUPS = env("SOCIALACCOUNT_ALLOW_SIGNUPS", default=ACCOUNT_ALLOW_SIGNUPS)
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_EMAIL_VERIFICATION = env("SOCIALACCOUNT_EMAIL_VERIFICATION", default=ACCOUNT_EMAIL_VERIFICATION)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "offline",
        },
        "OAUTH_PKCE_ENABLED": True,
    },
    "microsoft": {
        "OAUTH_PKCE_ENABLED": True,
    },
}

CSP_DEFAULT_SRC = ["'none'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "polyfill.io",
    "cdn.jsdelivr.net",
    "'unsafe-eval'",
    "'unsafe-inline'",
    *env.list("CSP_SCRIPT_SRC", default=[]),
]
CSP_STYLE_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "'unsafe-inline'",
    *env.list("CSP_STYLE_SRC", default=[]),
]
CSP_FONT_SRC = CSP_STYLE_SRC + env.list("CSP_FONT_SRC", default=[])
CSP_IMG_SRC = ["'self'", "data:", *env.list("CSP_IMG_SRC", default=[])]
CSP_BASE_URI = ["'none'", *env.list("CSP_BASE_URI", default=[])]
CSP_CONNECT_SRC = ["'self'", "maxcdn.bootstrapcdn.com", *env.list("CSP_CONNECT_SRC", default=[])]
CSP_FRAME_SRC = ["'self'", *env.list("CSP_FRAME_SRC", default=[])]
X_FRAME_OPTIONS = "SAMEORIGIN"
CSP_FRAME_ANCESTORS = ["'self'"]
CSP_MANIFEST_SRC = ["'self'", *env.list("CSP_MANIFEST_SRC", default=[])]
CSP_INCLUDE_NONCE_IN = ["script-src", *env.list("CSP_INCLUDE_NONCE_IN", default=[])]

HCAPTCHA_ENABLED = env("HCAPTCHA_ENABLED", default=True if TESTING else False)
CF_TURNSTILE_ENABLED = env("CF_TURNSTILE_ENABLED", default=False if TESTING else False)
if HCAPTCHA_ENABLED and CF_TURNSTILE_ENABLED:
    raise ImproperlyConfigured("HCAPTCHA_ENABLED and CF_TURNSTILE_ENABLED cannot both be enabled")

HCAPTCHA_VERIFY_URL = env("VERIFY_URL", default="https://hcaptcha.com/siteverify")
if HCAPTCHA_ENABLED and not TESTING:
    HCAPTCHA_SITE_KEY = env("HCAPTCHA_SITE_KEY")
    HCAPTCHA_SECRET_KEY = env("HCAPTCHA_SECRET_KEY")

CF_TURNSTILE_VERIFY_URL = env(
    "CF_TURNSTILE_VERIFY_URL",
    default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
)
if CF_TURNSTILE_ENABLED and not TESTING:
    CF_TURNSTILE_SITE_KEY = env("CF_TURNSTILE_SITE_KEY")
    CF_TURNSTILE_SECRET_KEY = env("CF_TURNSTILE_SECRET_KEY")

if TESTING:
    HCAPTCHA_SITE_KEY = "10000000-ffff-ffff-ffff-000000000001"
    HCAPTCHA_SECRET_KEY = "0x0000000000000000000000000000000000000000"
    CF_TURNSTILE_SITE_KEY = "1x00000000000000000000AA"
    CF_TURNSTILE_SECRET_KEY = "1x0000000000000000000000000000000AA"

if HCAPTCHA_ENABLED:
    CSP_SCRIPT_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_STYLE_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_CONNECT_SRC += ["hcaptcha.com", "*.hcaptcha.com"]
    CSP_FRAME_SRC += ["hcaptcha.com", "*.hcaptcha.com"]

if CF_TURNSTILE_ENABLED:
    CSP_SCRIPT_SRC += ["challenges.cloudflare.com"]
    CSP_STYLE_SRC += ["challenges.cloudflare.com"]
    CSP_CONNECT_SRC += ["challenges.cloudflare.com"]
    CSP_FRAME_SRC += ["challenges.cloudflare.com"]
