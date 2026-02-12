import logging

from celery import shared_task, group

from apps.cloud_storage.integrations.s3.storage import S3StorageClient
from apps.cloud_storage.services.files.delete_file import permanently_delete_user_files
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Subscription

logger = logging.getLogger("aerobox")


@shared_task
def clear_all_deleted_files_from_user(user_id, older_than_days=None):
    storage = S3StorageClient()
    permanently_delete_user_files(
        storage=storage,
        user_id=user_id,
        older_than_days=older_than_days,
    )


@shared_task
def delete_old_files():
    """
    Find all users with a free active subscription and dispatch
    a parallel task to clean their soft-deleted files older than 30 days.
    """
    free_user_ids = (
        Subscription.objects.filter(
            plan__is_free=True, status=SubscriptionStatusChoices.ACTIVE.value
        )
        .values_list("user_id", flat=True)
        .distinct()
    )

    logger.info(
        "Starting delete_old_files task: %s user(s) with free active subscriptions found.",
        free_user_ids.count(),
        extra={"user_ids": list(free_user_ids)},
    )

    job_args = [
        clear_all_deleted_files_from_user.s(user_id, 30) for user_id in free_user_ids
    ]
    job = group(job_args)
    job.apply_async()
