import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

from config.exceptions import DomainError

logger = logging.getLogger("aerobox")


class FileUploadError(APIException):
    """
    Custom exception for handling file upload errors without exposing backend details.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _(
        "An error occurred while processing your file. Please try again later."
    )
    default_code = "file_upload_error"

    def __init__(self, detail=None):
        if detail:
            logger.error(f"File upload error: {detail}", exc_info=True)
        super().__init__(detail or self.default_detail)


class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = _("This link is no longer available.")
    default_code = "gone"


class FolderSharingNotAllowed(DomainError):
    default_message = "User's current plan does not allow sharing folders."


class ShareLinkLimitReached(DomainError):
    default_message = "User exceeded the maximum number of active share links."


class ShareLinkExpirationTooLong(Exception):
    default_message = (
        "Share link expiration exceeds the maximum duration allowed by the user's plan."
    )


class ShareLinkPasswordNotAllowed(Exception):
    default_message = "User can not use password by his current plan."
