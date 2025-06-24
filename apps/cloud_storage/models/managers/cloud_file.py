from django.db import models

from apps.cloud_storage.constants.cloud_files import SUCCESS


class CloudFileQuerySet(models.QuerySet):
    def not_deleted(self):
        return self.filter(deleted_at__isnull=True)

    def for_user(self, user):
        return self.filter(user=user)

    def with_status(self, status):
        return self.filter(status=status)

    def success(self):
        return self.with_status(SUCCESS)


class CloudFileManager(models.Manager):
    """Custom manager that filters out soft-deleted records."""

    def get_queryset(self):
        return CloudFileQuerySet(self.model, using=self._db).not_deleted()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def user_success_files(self, user):
        return self.for_user(user).success()


class DeletedCloudFileManager(models.Manager):
    def get_queryset(self):
        return CloudFileQuerySet(self.model, using=self._db).filter(deleted_at__isnull=False)
