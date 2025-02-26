import secrets

from .base import *

DEBUG = True
SECRET_KEY = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,  # Prevents re-initializing existing loggers
    "handlers": {
        "null": {
            "class": "logging.NullHandler",  # Completely swallows logs
        },
    },
    "loggers": {
        "django": {
            "handlers": ["null"],  # Swallow all Django logs
            "level": "CRITICAL",   # Ignore anything below CRITICAL
            "propagate": False,    # Prevent logs from bubbling up
        },
        "aerobox":  {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        }
    },
}


# AWS S3
AWS_STORAGE_BUCKET_NAME = "test-bucket"
AWS_S3_BASE_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_BUCKET_REGION}.amazonaws.com"

# Celery
CELERY_TASK_ALWAYS_EAGER = True

STRIPE_SECRET_KEY = "test"
STRIPE_WEBHOOK_SECRET = "test"
