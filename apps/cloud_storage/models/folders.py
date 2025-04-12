from django.conf import settings
from django.db import models

from config.models.timestampable import Timestampable


class Folder(Timestampable):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="subfolders",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="folders",
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        unique_together = ("user", "name", "parent")

    def __str__(self):
        return f"{self.name} (ID:{self.id}) - {self.user}"
