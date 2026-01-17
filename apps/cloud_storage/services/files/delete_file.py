from django.utils import timezone


def soft_delete_file(file):
    file.deleted_at = timezone.now()
    file.folder = None
    file.save(update_fields=["deleted_at", "folder_id"])
