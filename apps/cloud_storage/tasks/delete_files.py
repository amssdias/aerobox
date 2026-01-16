import logging
from datetime import timedelta

from celery import shared_task, group
from django.utils.timezone import now

from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.models import CloudFile
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Subscription

logger = logging.getLogger("aerobox")


@shared_task
def clear_all_deleted_files_from_user(user_id, older_than_days=None):
    deleted_files = CloudFile.deleted.filter(user_id=user_id)

    if older_than_days is not None:
        deleted_files = get_deleted_files_before_filter(deleted_files, older_than_days)

    s3_service = S3Service()
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
    threshold_date = now() - timedelta(days=older_than_days)
    return qs.filter(deleted_at__lte=threshold_date)


@shared_task
def delete_old_files():
    """
    Find all users with a free active subscription and dispatch
    a parallel task to clean their soft-deleted files older than 30 days.
    """
    free_user_ids = (
        Subscription.objects
        .filter(plan__is_free=True, status=SubscriptionStatusChoices.ACTIVE.value)
        .values_list("user_id", flat=True)
        .distinct()
    )

    logger.info(
        "Starting delete_old_files task: %s user(s) with free active subscriptions found.",
        free_user_ids.count(),
        extra={"user_ids": list(free_user_ids)},
    )

    job_args = [clear_all_deleted_files_from_user.s(user_id, 30) for user_id in free_user_ids]
    job = group(job_args)
    job.apply_async()
