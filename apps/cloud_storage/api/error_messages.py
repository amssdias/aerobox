from django.utils.translation import gettext as _

from apps.cloud_storage.choices.cloud_file_error_code_choices import CloudFileErrorCode

ERROR_MESSAGES = {
    CloudFileErrorCode.FILE_NOT_FOUND_IN_S3.value: _(
        "File upload verification failed: the file could not be found in storage. "
        "Please try uploading it again."
    ),
    CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value: _(
        "You have reached your storage limit. This file cannot be kept. "
        "Please delete some files or upgrade your plan and try again."
    ),
    CloudFileErrorCode.FILE_TOO_LARGE.value: _(
        "This file is too large for your current plan. "
        "Please upload a smaller file or upgrade your plan."
    ),
    CloudFileErrorCode.UNKNOWN_S3_ERROR.value: _(
        "Something went wrong while uploading your file. "
        "Please try again in a moment."
    ),
}


def get_error_message(error_code: str) -> str:
    if not error_code:
        return _("An error occurred while verifying your file upload.")
    return ERROR_MESSAGES.get(
        error_code,
        _("An error occurred while verifying your file upload."),
    )
