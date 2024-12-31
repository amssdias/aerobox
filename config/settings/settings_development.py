from .base import *


DEBUG = True
SECRET_KEY = "pzm!wg763dggm*8#f!vi$jp&gp^l!2%j55gqyb^9t&sgwcn^53"

AUTH_PASSWORD_VALIDATORS = []

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
