from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from config.models.timestampable import Timestampable


class CloudFiles(Timestampable):
    name = models.CharField(max_length=255)
    size = models.BigIntegerField()
    file_type = models.CharField(max_length=50)
    path = models.CharField(max_length=30)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="files", 
        on_delete=models.SET_NULL,
        null=True,
    )
    file_uploaded = models.FileField()

    class Meta:
        verbose_name = _("Cloud File")
        verbose_name_plural = _("Cloud Files")
