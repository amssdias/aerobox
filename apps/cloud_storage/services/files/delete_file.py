from django.utils import timezone


def soft_delete_file(file):
    file.deleted_at = timezone.now()
    file.folder = None
    file.save(update_fields=["deleted_at", "folder_id"])


def permanent_delete_file(storage, file):
    storage.delete_file(object_name=file.s3_key)
    file.permanent_delete()
