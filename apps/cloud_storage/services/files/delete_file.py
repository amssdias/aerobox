import logging
from datetime import timedelta

from django.utils import timezone

from apps.cloud_storage.models import CloudFile

logger = logging.getLogger("aerobox")


def soft_delete_file(file):
    file.deleted_at = timezone.now()
    file.folder = None
    file.save(update_fields=["deleted_at", "folder_id"])


def permanent_delete_file(storage, file):
    storage.delete_file(object_name=file.s3_key)
    file.permanent_delete()


def permanently_delete_user_files(storage, user_id, older_than_days):
    deleted_files = CloudFile.deleted.filter(user_id=user_id)

    if older_than_days is not None:
        deleted_files = get_deleted_files_before_filter(deleted_files, older_than_days)

    failed_s3_keys = []

    for deleted_file in deleted_files:
        try:
            storage.delete_file(object_name=deleted_file.s3_key)
        except Exception as e:
            failed_s3_keys.append(deleted_file.s3_key)
            logger.error(
                "Failed to delete file from S3.",
                extra={
                    "user_id": user_id,
                    "file_id": deleted_file.id,
                    "s3_key": deleted_file.s3_key,
                    "error": str(e),
                },
            )

    # Only delete from DB if all S3 deletions succeeded
    successfully_deleted_files = deleted_files.exclude(s3_key__in=failed_s3_keys)
    deleted_count = successfully_deleted_files.delete()[0]

    logger.info(
        "Permanently deleted %s file(s) from DB and S3 for user_id=%s.",
        deleted_count,
        user_id,
    )

    if failed_s3_keys:
        logger.warning(
            "Some files could not be deleted from S3 for user_id=%s.",
            user_id,
            extra={"failed_keys": failed_s3_keys},
        )


def get_deleted_files_before_filter(qs, older_than_days):
    threshold_date = timezone.now() - timedelta(days=older_than_days)
    return qs.filter(deleted_at__lte=threshold_date)
