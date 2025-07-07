from django.db import models
from django.utils.timezone import now


class SoftDeleteModel(models.Model):
    """
    Abstract model that provides a 'deleted_at' field for soft deletes.
    """
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self, *args, **kwargs):
        """Override delete() to perform a soft delete."""
        self.deleted_at = now()
        self.save(update_fields=["deleted_at"])

    def permanent_delete(self, *args, **kwargs):
        super(SoftDeleteModel, self).delete(*args, **kwargs)

    def restore(self):
        """Restore a soft-deleted instance."""
        self.deleted_at = None
        self.save()

    class Meta:
        abstract = True
