from apps.cloud_storage.domain.exceptions.file import FileNotDeletedError


def restore_deleted_file(file):
    if not file.deleted_at:
        raise FileNotDeletedError()

    file.deleted_at = None
    file.save(update_fields=["deleted_at"])
