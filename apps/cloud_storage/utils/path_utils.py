from apps.cloud_storage.constants.cloud_files import USER_PREFIX


def build_s3_path(user_id, file_name):
    """Builds the full S3 object path for storing a file."""
    user_prefix = USER_PREFIX.format(user_id)
    return f"{user_prefix}/{file_name}".strip("/")
