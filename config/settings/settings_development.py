from .base import *


DEBUG = True
AUTH_PASSWORD_VALIDATORS = []

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
