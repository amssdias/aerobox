from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.cloud_storage.constants.cloud_files import PENDING, SUCCESS, FAILED
from config.models.soft_delete import SoftDeleteModel
from config.models.timestampable import Timestampable


class CloudFile(Timestampable, SoftDeleteModel):
    STATUS = (
        (PENDING, _("Pending")),
        (SUCCESS, _("Success")),
        (FAILED, _("Failed")),
    )

    file_name = models.CharField(
        max_length=255,
        help_text=_("The intended name of the file to be stored in S3.")
    )
    path = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("The S3 path where the file is stored.")
    )
    size = models.BigIntegerField(
        help_text=_("The size of the file in bytes. This can be updated after the file is uploaded.")
    )
    content_type = models.CharField(
        max_length=50,
        help_text=_("The MIME type of the file (e.g., 'image/jpeg', 'application/pdf').")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="files", 
        on_delete=models.SET_NULL,
        null=True,
        help_text=_("The user who uploaded the file (owner).")
    )
    status = models.CharField(
        max_length=8,
        choices=STATUS, 
        default=PENDING,
        help_text=_("The current status of the file upload process.")
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
    # upload_attempts = models.PositiveIntegerField(
    #     default=0,
    #     help_text=_("The number of times an upload attempt was made for this file.")
    # )

    class Meta:
        verbose_name = _("Cloud File")
        verbose_name_plural = _("Cloud Files")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["file_name"]),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.user})"

    def get_relative_path(self):
        """Returns only the part of the path that should be exposed to the user."""
        return "/".join(self.path.split("/")[2:])  # Removes 'user/user_id/'

    @property
    def file_url(self):
        return f"{settings.AWS_S3_BASE_URL}/{self.path}"
