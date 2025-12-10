import secrets
from typing import Optional

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from config.models import Timestampable


def generate_share_token():
    return secrets.token_urlsafe(16)


class ShareLink(Timestampable):
    """
    Model backing the 'file_sharing' feature. A ShareLink is a container that
    references one or more files or folders and exposes them via a public token.
    Behavior such as folder sharing, password protection, expiration, and link
    limits depends on the user’s plan configuration.
    """

    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_share_token,
        help_text=_("Public token used to identify the shared link."),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="share_links",
        on_delete=models.CASCADE,
    )

    files = models.ManyToManyField(
        "cloud_storage.CloudFile",
        blank=True,
        related_name="share_links",
        help_text=_("Files included in this shared link."),
    )
    folders = models.ManyToManyField(
        "cloud_storage.Folder",
        blank=True,
        related_name="share_links",
        help_text=_("Folders included in this shared link."),
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date when the link will automatically expire."),
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date when the user manually deactivated this link."),
    )

    password = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_("Hashed password required to access this link, if enabled."),
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["owner", "-created_at"], name="sharelink_owner_created_idx"
            ),
        ]

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def set_password(self, raw_password: Optional[str]):
        if raw_password:
            self.password = make_password(raw_password)

    def check_password(self, raw_password) -> bool:
        if not self.password:
            return True
        if not raw_password:
            return False
        return check_password(raw_password, self.password)

    def can_access_file(self, cloud_file) -> bool:
        if self.files.filter(id=cloud_file.id).exists():
            return True

        if not cloud_file.folder_id:
            return False

        root = cloud_file.get_root_folder()
        if root and self.folders.filter(id=root.id).exists():
            return True

        return False
