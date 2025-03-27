from django.db import models
from django.utils.translation import gettext_lazy as _


class FeatureCodeChoices(models.TextChoices):
    CLOUD_STORAGE = "cloud_storage", _("Cloud Storage")
    FILE_PREVIEW = "file_preview", _("File Preview")
    FILE_SHARING = "file_sharing", _("File Sharing via Link")
    FOLDER_CREATION = "folder_creation", _("Folder Creation")
    BASIC_SUPPORT = "basic_support", _("Basic Email Support")
