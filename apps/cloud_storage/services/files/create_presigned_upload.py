import logging
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from apps.cloud_storage.domain.exceptions.exceptions import FileUploadError
from apps.cloud_storage.utils.hash_utils import generate_unique_hash
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.cloud_storage.utils.size_utils import get_user_used_bytes

logger = logging.getLogger("aerobox")


@dataclass(frozen=True)
class PreparedUpload:
    file_path: str
    presigned_url: str


def prepare_file_upload(storage, user, file_name, content_type):
    # Generate path to upload
    hashed_file_name = generate_unique_hash(file_name)
    file_path = build_s3_path(
        user_id=user.id,
        file_name=hashed_file_name,
    )

    subscription = user.active_subscription
    plan = subscription.plan

    limit_bytes = plan.max_storage_bytes
    used_bytes = get_user_used_bytes(user)

    # Remaining usable storage under the user's plan
    available_storage_bytes = max(limit_bytes - used_bytes, 0)

    # Per-file limit defined by the plan
    max_file_upload_bytes = plan.max_file_upload_size_bytes

    # Final allowed size = the minimum of:
    #   - remaining storage
    #   - per-file limit
    max_bytes = min(available_storage_bytes, max_file_upload_bytes)

    try:
        presigned_url = storage.create_presigned_post_url(
            object_key=file_path,
            user_id=user.id,
            max_bytes=max_bytes,
            content_type=content_type,
        )
        if not presigned_url:
            raise ValueError(
                _(
                    "Something went wrong while preparing your file upload. Please try again."
                )
            )
    except Exception as e:
        logger.error(f"File upload error for path {file_path}: {str(e)}", exc_info=True)
        raise FileUploadError()

    return PreparedUpload(file_path=file_path, presigned_url=presigned_url)
