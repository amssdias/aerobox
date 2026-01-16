from django.db import transaction

from apps.cloud_storage.choices.cloud_file_error_code_choices import CloudFileErrorCode
from apps.cloud_storage.constants.cloud_files import FAILED
from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.services.storage.cloud_file_sync_service import CloudFileSyncService
from apps.cloud_storage.utils.size_utils import get_user_used_bytes


class FileUploadFinalizerService:
    def __init__(self, sync_service=None, storage=None):
        self.sync_service = sync_service or CloudFileSyncService()
        self.storage = storage or S3Service()

    @transaction.atomic
    def finalize(self, cloud_file):
        """
        Called when frontend Patches status=SUCCESS.

        1. Sync real size from S3
        2. If S3 file missing → mark FAILED
        3. If size increased → re-check plan limits
           - if over quota → delete from S3 + mark FAILED
        """

        synced_file, size_changed = self.sync_service.sync(cloud_file)

        if not synced_file:
            self.mark_as_failed(
                cloud_file,
                error_code=CloudFileErrorCode.FILE_NOT_FOUND_IN_S3.value,
                error_message="File not found in storage during upload verification."
            )
            return False

        if size_changed and self.is_over_quota(cloud_file):
            self.storage.delete_file_from_s3(synced_file.s3_key)
            self.mark_as_failed(
                cloud_file,
                error_code=CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value,
                error_message="User exceeded storage quota after final size verification."
            )
            return False

        return True

    @staticmethod
    def mark_as_failed(cloud_file, error_code: str, error_message: str) -> None:
        cloud_file.status = FAILED
        cloud_file.error_code = error_code
        cloud_file.error_message = error_message
        cloud_file.save(update_fields=["status", "error_code", "error_message"])

    @staticmethod
    def is_over_quota(cloud_file) -> bool:
        user = cloud_file.user
        used_bytes = get_user_used_bytes(user)
        subscription = user.active_subscription
        plan = subscription.plan
        limit_bytes = plan.max_storage_bytes
        return used_bytes > limit_bytes
