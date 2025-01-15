from .base import *


DEBUG = True
SECRET_KEY = "pzm!wg763dggm*8#f!vi$jp&gp^l!2%j55gqyb^9t&sgwcn^53"

AUTH_PASSWORD_VALIDATORS = []

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FRONTEND_DOMAIN = "localhost:3000"
