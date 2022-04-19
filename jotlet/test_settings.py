import mimetypes
import os
from pathlib import Path

mimetypes.add_type("text/javascript", ".js", True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "testing-key"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost"]

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

ROOT_URLCONF = "jotlet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
            os.path.join(BASE_DIR, "accounts", "templates", "allauth"),
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

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

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
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_ROOT = "static/"
STATIC_URL = "static/"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

MEDIA_ROOT = "media/"
MEDIA_URL = "media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "boards:index"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

CRISPY_FAIL_SILENTLY = not DEBUG

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "KEY_PREFIX": "jotlet",
    }
}

CACHEOPS_DEFAULTS = {"timeout": 60 * 60}
CACHEOPS = {"*.*": {"ops": ()}}
CACHEOPS_ENABLED = False

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

Q_CLUSTER = {
    "name": "DjangORM",
    "testing": True,
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "testing@test.com"

PROMETHEUS_ENABLED = False

CSP_DEFAULT_SRC = ["'none'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "cdn.jsdelivr.net",
    "polyfill.io",
    "unpkg.com",
    "'unsafe-inline'",
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
CSP_INCLUDE_NONCE_IN = ["script-src", "style-src"]

DEBUG_TOOLBAR_ENABLED = False
