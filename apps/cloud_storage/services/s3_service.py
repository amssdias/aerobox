import logging
import mimetypes

from botocore.exceptions import NoCredentialsError, ClientError
from django.conf import settings

from .aws_client import AWSClient

logger = logging.getLogger("aerobox")


class S3Service:
    def __init__(self):
        self.s3_client = AWSClient("s3").get_client()

    def generate_presigned_upload_url(
        self,
        object_name,
        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
        expiration=settings.AWS_PRESIGNED_EXPIRATION_TIME,
    ):
        """
        Generates a presigned URL for uploading a file to S3.

        :param bucket_name: Name of the S3 bucket
        :param object_name: S3 key (object path) where the file will be stored
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as a string or None if there is an error
        """
        try:
            content_type, _ = mimetypes.guess_type(object_name)
            presigned_url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_name,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration,
            )
            return presigned_url
        except (NoCredentialsError, ClientError) as e:
            logger.exception(f"Error generating presigned URL: {e}")
            return None

    def generate_presigned_download_url(
        self, object_name, bucket_name=settings.AWS_STORAGE_BUCKET_NAME, expiration=3600
    ):
        """
        Generates a presigned URL for downloading a file from S3.

        :param bucket_name: Name of the S3 bucket
        :param object_name: S3 key (file path) in the bucket
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as a string or None if the file does not exist or there is an error
        """
        try:

            # Check if the file exists first
            self.s3_client.head_object(Bucket=bucket_name, Key=object_name)

            presigned_url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": object_name,
                },
                ExpiresIn=expiration,
            )
            return presigned_url

        except ClientError as e:

            if e.response["Error"]["Code"] == "404":
                logger.error(
                    f"File '{object_name}' not found in S3 bucket '{bucket_name}'."
                )
                return None
            else:
                logger.error(f"Error generating presigned download URL: {e}")
                return None

        except NoCredentialsError:
            logger.critical("AWS credentials not found.")
            return None

    def rename_file(
        self, old_key: str, new_key: str, bucket_name=settings.AWS_STORAGE_BUCKET_NAME
    ) -> bool:
        """
        Renames a file in S3 by copying it to a new key and deleting the original.

        :param bucket_name: The S3 bucket name.
        :param old_key: The current file key in S3.
        :param new_key: The new file key in S3.
        :return: True if successful, False otherwise.
        """
        try:
            # Copy file to the new location
            self.s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": old_key},
                Key=new_key,
            )

            # Delete the old file
            self.s3_client.delete_object(Bucket=bucket_name, Key=old_key)

            return True
        except Exception as e:
            logger.error(f"Error renaming file in S3: {e}")
            return False
