import logging

from celery import shared_task
from django.db import transaction

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services import S3Service

logger = logging.getLogger("aerobox")


@shared_task
def delete_all_files_from_user(user_id):
    deleted_files = CloudFile.deleted.filter(user_id=user_id)

    s3_service = S3Service()

    deleted_count = 0
    failed_s3_keys = []

    for deleted_file in deleted_files:
        try:
            s3_service.delete_file_from_s3(object_name=deleted_file.s3_key)
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

    with transaction.atomic():
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
