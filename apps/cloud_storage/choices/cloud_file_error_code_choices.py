from django.db import models
from django.utils.translation import gettext_lazy as _


class CloudFileErrorCode(models.TextChoices):
    FILE_NOT_FOUND_IN_S3 = "file_not_found_in_s3", _("File not found in S3")
    STORAGE_QUOTA_EXCEEDED = "storage_quota_exceeded", _("Storage quota exceeded")
    FILE_TOO_LARGE = "file_too_large", _("File too large for plan")
    UNKNOWN_S3_ERROR = "unknown_s3_error", _("Unknown S3 error")
