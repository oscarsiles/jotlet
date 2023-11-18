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

mimetypes.add_type("text/javascript", ".js", strict=True)

env = environ.Env()
env.smart_cast = False
BASE_DIR = Path(__file__).resolve().parent.parent
test_env_file = Path(BASE_DIR) / ".env.test"
if TESTING and Path.exists(test_env_file):
    environ.Env.read_env(test_env_file)
elif not TESTING:
    environ.Env.read_env(Path(BASE_DIR) / ".env")

SECRET_KEY = env.str("SECRET_KEY", default="unsafe-secret-key")

# workaround for poetry packages that aren't "installed"
# https://github.com/wemake-services/wemake-python-styleguide/blob/master/docs/conf.py#L22-L37
VERSION = ""
with Path.open(Path(BASE_DIR) / "pyproject.toml", mode="rb") as pyproject:
    VERSION = tomli.load(pyproject)["tool"]["poetry"]["version"]

DEBUG = env.bool("DEBUG", default=TESTING)
DEBUG_TOOLBAR_ENABLED = env.bool("DEBUG_TOOLBAR_ENABLED", default=False)

SENTRY_ENABLED = env.bool("SENTRY_ENABLED", default=False)
if SENTRY_ENABLED and not DEBUG and not TESTING:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    SENTRY_DSN = env.str("SENTRY_DSN")

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.01),
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=env.bool("SENTRY_SEND_DEFAULT_PII", default=False),
        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        release=VERSION,
        environment=env.str("SENTRY_ENVIRONMENT", default="production"),
    )
    CSP_REPORT_URI = env.str("SENTRY_SECURITY_ENDPOINT", default=None)


ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_HEADERS = [*list(default_headers), "link"]
CORS_EXPOSE_HEADERS = ["link"]

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)
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
            Path(BASE_DIR) / "templates",
            Path(BASE_DIR) / "jotlet" / "templates",
            Path(BASE_DIR) / "accounts" / "templates" / "allauth",
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
        "NAME": env.str("DB_NAME", default="jotlet"),
        "USER": env.str("DB_USER", default="jotlet"),
        "PASSWORD": env.str("DB_PASSWORD"),
        "HOST": env.str("DB_HOST", default="postgres"),
        "PORT": env.str("DB_PORT", default="5432"),
    }
}


CONN_MAX_AGE = env.int("CONN_MAX_AGE", default=None)
CONN_HEALTH_CHECKS = CONN_MAX_AGE is None or CONN_MAX_AGE > 0  # only check if we're using persistent connections

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 24 * 30)  # 30 days

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

AXES_ENABLED = env.bool("AXES_ENABLED", default=True)

if TESTING:
    os.environ["AXES_IPWARE_PROXY_COUNT"] = "1"
    SILENCED_SYSTEM_CHECKS = ["axes.W001"]
if AXES_ENABLED and not TESTING:
    AXES_HANDLER = env.str(
        "AXES_HANDLER",
        default="axes.handlers.dummy.AxesDummyHandler" if TESTING else "axes.handlers.database.AxesDatabaseHandler",
    )
    AXES_USERNAME_FORM_FIELD = "login"
    AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
    AXES_COOLOFF_TIME = timedelta(minutes=env("AXES_COOLOFF_MINUTES", default=15))
    AXES_LOCKOUT_URL = "/accounts/lockout/"
    AXES_LOCKOUT_PARAMETERS = env.list("AXES_LOCKOUT_PARAMETERS", default=["username", "ip_address"])
    AXES_IPWARE_PROXY_COUNT = env.int("AXES_IPWARE_PROXY_COUNT", default=None)
    AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", *AUTHENTICATION_BACKENDS]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

USE_I18N = False
LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="en-us")

USE_TZ = True
TIME_ZONE = env.str("TIME_ZONE", default="UTC")

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "boards:index"
LOGOUT_REDIRECT_URL = "boards:index"

USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    # aws settings
    AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME", default="eu-west-2")
    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
    AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = env.str("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_S3_SIGNATURE_VERSION = env.str("AWS_S3_SIGNATURE_VERSION", default="s3v4")
    AWS_S3_OBJECT_PARAMETERS = env.str("AWS_S3_OBJECT_PARAMETERS", default={"CacheControl": "max-age=2592000"})
    AWS_DEFAULT_ACL = env.str("AWS_DEFAULT_ACL", default=None)
    AWS_IS_GZIPPED = env.bool("AWS_IS_GZIPPED", default=False)
    # s3 public media settings
    THUMBNAIL_FORCE_OVERWRITE = True
    PUBLIC_MEDIA_LOCATION = env.str("PUBLIC_MEDIA_LOCATION", default="media")
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
else:
    MEDIA_URL = "media/"
    if TESTING:
        import tempfile

        MEDIA_ROOT = f"{tempfile.mkdtemp()}/"
        WHITENOISE_AUTOREFRESH = True
    else:
        MEDIA_ROOT = str(Path(BASE_DIR) / "media")

MAX_IMAGE_WIDTH = env.int("MAX_IMAGE_WIDTH", default=500 if TESTING else 3840)
MAX_IMAGE_HEIGHT = env.int("MAX_IMAGE_HEIGHT", default=500 if TESTING else 2160)
SMALL_THUMBNAIL_WIDTH = env.int("SMALL_THUMBNAIL_WIDTH", default=300)
SMALL_THUMBNAIL_HEIGHT = env.int("SMALL_THUMBNAIL_HEIGHT", default=200)
MAX_POST_IMAGE_FILE_SIZE = env.int("MAX_IMAGE_FILE_SIZE", default=1024 * 1024 * 2)
MAX_POST_IMAGE_COUNT = env.int("MAX_POST_IMAGE_COUNT", default=100)
MAX_POST_IMAGE_WIDTH = env.int("MAX_POST_IMAGE_WIDTH", default=400)
MAX_POST_IMAGE_HEIGHT = env.int("MAX_POST_IMAGE_HEIGHT", default=MAX_POST_IMAGE_WIDTH)

THUMBNAIL_ALTERNATIVE_RESOLUTIONS = env.list("THUMBNAIL_ALTERNATIVE_RESOLUTIONS", default=[2])

STATIC_URL = "static/"
STATIC_ROOT = Path(BASE_DIR) / "static"
STATICFILES_DIRS = [Path(BASE_DIR) / "jotlet" / "static"]

STATIC_COMPRESSED = env.bool("STATIC_COMPRESSED", default=not TESTING)
if TESTING:
    STATIC_BACKEND = "django.core.files.storage.InMemoryStorage"
elif STATIC_COMPRESSED:
    STATIC_BACKEND = "whitenoise.storage.CompressedManifestStaticFilesStorage"
else:
    STATIC_BACKEND = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "jotlet.storage_backends.PublicMediaStorage"
        if USE_S3
        else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {"BACKEND": STATIC_BACKEND},
}
THUMBNAIL_STORAGE = STORAGES["default"]["BACKEND"]

REDIS_HOST = env.str("REDIS_HOST", default="localhost")
REDIS_PORT = env.int("REDIS_PORT", default=6379)
REDIS_URL = env.str("REDIS_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}")

CACHES = {
    "default": {
        "BACKEND": env.str("REDIS_BACKEND", default="django_redis.cache.RedisCache"),
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "jotlet_test" if TESTING else "jotlet",
        "OPTIONS": {
            # this connection pool is also used for Huey
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PARSER_CLASS": "redis.connection._HiredisParser",
        },
    },
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "prefix": "jotlet_test" if TESTING else "jotlet",
            "capacity": 500,
        },
    },
}

CACHEOPS_ENABLED = env.bool("CACHEOPS_ENABLED", default=True)
CACHEOPS_DEFAULTS = {"timeout": env.int("CACHEOPS_TIMEOUT", default=31556952)}
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
CACHEOPS_INSIDEOUT = env.bool("CACHEOPS_INSIDEOUT", default=True)

CACHEOPS_REDIS = {"host": REDIS_HOST, "port": REDIS_PORT, "db": 13, "socket_timeout": 3} if TESTING else REDIS_URL

HUEY = {
    "huey_class": "jotlet.huey.DjangoPriorityRedisExpiryHuey",  # custom class that uses django-redis pool
    "immediate": DEBUG or TESTING,
    "immediate_use_memory": False,
    "consumer": {
        "workers": env.int("HUEY_WORKERS", default=4),
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

EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="hueymail.backends.EmailBackend")

HUEY_EMAIL_BACKEND = env.str(
    "HUEY_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if TESTING
    else "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = env.str("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="")
FEEDBACK_EMAIL = env.str("FEEDBACK_EMAIL", default=None)

ANYMAIL = {
    "MAILGUN_API_KEY": env.str("MAILGUN_API_KEY", default=""),
    "MAILGUN_API_URL": env.str("MAILGUN_API_URL", default="https://api.eu.mailgun.net/v3"),
    "MAILGUN_SENDER_DOMAIN": env.str("MAILGUN_SENDER_DOMAIN", default=""),
    "SENDGRID_API_KEY": env.str("SENDGRID_API_KEY", default=""),
}

ACCOUNT_ADAPTER = "accounts.adapter.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.CustomSocialAccountAdapter"
ACCOUNT_EMAIL_REQUIRED = env.bool("ACCOUNT_EMAIL_REQUIRED", default=True)
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = env.str("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_MAX_EMAIL_ADDRESSES = 1
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if DEBUG else "https"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_ALLOW_SIGNUPS = env.bool("ACCOUNT_ALLOW_SIGNUPS", default=True)

SOCIALACCOUNT_ALLOW_SIGNUPS = env.bool("SOCIALACCOUNT_ALLOW_SIGNUPS", default=ACCOUNT_ALLOW_SIGNUPS)
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_EMAIL_VERIFICATION = env.bool("SOCIALACCOUNT_EMAIL_VERIFICATION", default=ACCOUNT_EMAIL_VERIFICATION)

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

HCAPTCHA_ENABLED = env.bool("HCAPTCHA_ENABLED", default=False)
CF_TURNSTILE_ENABLED = env.bool("CF_TURNSTILE_ENABLED", default=False)
if HCAPTCHA_ENABLED and CF_TURNSTILE_ENABLED:
    msg = "HCAPTCHA_ENABLED and CF_TURNSTILE_ENABLED cannot both be enabled"
    raise ImproperlyConfigured(msg)

HCAPTCHA_VERIFY_URL = env.str("VERIFY_URL", default="https://hcaptcha.com/siteverify")
if HCAPTCHA_ENABLED and not TESTING:
    HCAPTCHA_SITE_KEY = env.str("HCAPTCHA_SITE_KEY")
    HCAPTCHA_SECRET_KEY = env.str("HCAPTCHA_SECRET_KEY")

CF_TURNSTILE_VERIFY_URL = env.str(
    "CF_TURNSTILE_VERIFY_URL",
    default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
)
if CF_TURNSTILE_ENABLED and not TESTING:
    CF_TURNSTILE_SITE_KEY = env.str("CF_TURNSTILE_SITE_KEY")
    CF_TURNSTILE_SECRET_KEY = env.str("CF_TURNSTILE_SECRET_KEY")

if TESTING:
    # Use dummy keys for testing
    HCAPTCHA_SITE_KEY = "10000000-ffff-ffff-ffff-000000000001"
    HCAPTCHA_SECRET_KEY = "0x0000000000000000000000000000000000000000"  # noqa: S105
    CF_TURNSTILE_SITE_KEY = "1x00000000000000000000AA"
    CF_TURNSTILE_SECRET_KEY = "1x0000000000000000000000000000000AA"  # noqa: S105

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
