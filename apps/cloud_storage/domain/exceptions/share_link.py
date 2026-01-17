from config.exceptions import DomainError


class ShareLinkError(DomainError):
    default_message = "Share link error."
    default_code = "share_link_error"


class FolderSharingNotAllowed(ShareLinkError):
    default_message = "User's current plan does not allow sharing folders."
    default_code = "share_link_folder_sharing_not_allowed"


class ShareLinkLimitReached(ShareLinkError):
    default_message = "User exceeded the maximum number of active share links."
    default_code = "share_link_limit_reached"


class ShareLinkExpirationTooLong(ShareLinkError):
    default_message = (
        "Share link expiration exceeds the maximum duration allowed by the user's plan."
    )
    default_code = "share_link_expiration_too_long"


class ShareLinkPasswordNotAllowed(ShareLinkError):
    default_message = "User can not use password by his current plan."
    default_code = "share_link_password_not_allowed"
