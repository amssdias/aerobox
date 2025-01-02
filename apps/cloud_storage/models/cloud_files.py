from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from config.models.timestampable import Timestampable


class CloudFile(Timestampable):
    STATUS = (
        ("pending", _("Pending")),
        ("uploaded", _("Uploaded")),
        ("failed", _("Failed")),
    )

    file_name = models.CharField(
        max_length=255,
        help_text=_("The intended name of the file to be stored in S3.")
    )
    path = models.CharField(
        max_length=255,
        help_text=_("The S3 key or path where the file is stored.")
    )
    size = models.BigIntegerField(
        null=True, 
        blank=True,
        help_text=_("The size of the file in bytes. This can be updated after the file is uploaded.")
    )
    file_type = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text=_("The MIME type of the file (e.g., 'image/jpeg', 'application/pdf').")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="files", 
        on_delete=models.SET_NULL,
        null=True,
        help_text=_("The user who uploaded the file.")
    )
    status = models.CharField(
        max_length=8,
        choices=STATUS, 
        default="pending",
        help_text=_("The current status of the file upload process.")
    )
    checksum = models.CharField(
        max_length=64, 
        blank=True, 
        null=True,
        help_text=_("A checksum or hash (e.g., MD5, SHA256) to verify the integrity of the uploaded file.")
    )
    file_url = models.URLField(
        max_length=1024, 
        blank=True, 
        null=True,
        help_text=_("The URL to access the file in S3. Typically, this is generated after the file is uploaded.")
    )
    error_message = models.TextField(
        blank=True, 
        null=True,
        help_text=_("Any error message encountered during the file upload process.")
    )
    metadata = models.JSONField(
        blank=True, 
        null=True,
        help_text=_("Additional metadata related to the file, stored as a JSON object.")
    )


    class Meta:
        verbose_name = _("Cloud File")
        verbose_name_plural = _("Cloud Files")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["file_name"]),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.user})"
