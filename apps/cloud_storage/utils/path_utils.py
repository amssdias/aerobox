from apps.cloud_storage.constants.cloud_files import USER_PREFIX


def build_s3_path(user_id, file_name):
    """Builds the full S3 object path for storing a file."""
    user_prefix = USER_PREFIX.format(user_id)
    return f"{user_prefix}/{file_name}".strip("/")


def build_s3_object_path(user, file_name, folder=None):
    """
    Builds the full S3 object path for a file inside a folder (if provided),
    or at the root user level if no folder is specified.
    """
    if folder:
        folder_path = folder.build_path()
        return build_s3_path(user.id, f"{folder_path}{file_name}")
    return build_s3_path(user.id, file_name)
