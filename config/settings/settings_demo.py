from .base import *


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


CELERY_TASK_ALWAYS_EAGER = True
# SECURE_SSL_REDIRECT = True

# Protect against XSS & MIME type sniffing
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Prevent clickjacking
X_FRAME_OPTIONS = "DENY"

# Referrer policy to protect sensitive data
SECURE_REFERRER_POLICY = "same-origin"

# Use forwarded headers correctly (important for reverse proxy setups)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")

# Storages
STORAGES = {
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_BUCKET_REGION,
        },
        "LOCATION": "static/",
        "ACL": "public-read"
    }
}

STATIC_URL = f"https://s3.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}/static/"
