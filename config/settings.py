from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DJANGO_DEBUG=(bool, False))
# Read .env if present
environ.Env.read_env(BASE_DIR / ".env")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },

    "handlers": {
        # ========== console ==========
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },

        # ========== main file log ==========
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "project.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "standard",
        },

        # ========== Google Sheets logs ==========
        "sheets": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "sheets.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "standard",
        },
    },

    "loggers": {
        # Django internal logs
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        # Requests coming to DRF API
        "django.request": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Google Sheets integration logs
        "sheets": {
            "handlers": ["sheets", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # your project (any module)
        "app": {
            "handlers": ["file", "console"],
            "level": "INFO",
        },
    },
}

DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "apps.core",
    "apps.accounts",
    "apps.customers",
    "apps.orders",
    "apps.api",
]

AUTH_USER_MODEL = "accounts.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="portal"),
        "USER": env("DB_USER", default="portal"),
        "PASSWORD": env("DB_PASSWORD", default="portal"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
}

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = "noreply@example.com"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

TIME_ZONE = "Europe/Kyiv"
USE_TZ = True
LANGUAGE_CODE = "uk"

# --- TEMPLATES (обязательно для admin) ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # можно оставить пустым, но пусть будет
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.roles",
            ],
        },
    },
]

# --- MIDDLEWARE (порядок важен) ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",     # до auth
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # после sessions
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.middleware.request_logging.RequestLoggingMiddleware",
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Тип PK по умолчанию (убирает W042) ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Где лежит корневой urls.py
ROOT_URLCONF = "config.urls"

# Точки входа WSGI/ASGI (полезно и для dev)
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / "config" / "google-service-account.json"
FABRIC_COLORS_SHEET_ID = "1Dsr-7LdyjchAttYgvv8dmvByausJqw3NrlGX8wTwF7o"
FABRIC_COLORS_SHEET_NAME = "Тканини до ролет"


