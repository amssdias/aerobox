from django.db import models

class CloudFileManager(models.Manager):
    """Custom manager that filters out soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
