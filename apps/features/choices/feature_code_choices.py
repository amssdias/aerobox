from django.db import models
from django.utils.translation import gettext_lazy as _


class FeatureCodeChoices(models.TextChoices):
    CLOUD_STORAGE = "cloud_storage", _("Cloud Storage")
