import logging

from botocore.exceptions import NoCredentialsError, ClientError
from django.conf import settings

from integrations.aws.aws_client import AWSClient

logger = logging.getLogger("aerobox")


class S3Service:
    def __init__(self):
        self.s3_client = AWSClient("s3").get_client()

    def create_presigned_post_url(
        self,
            object_key: str,
            user_id: int,
            max_bytes: int,
            content_type: str,
    ):
        """
        Generate a presigned POST for direct-to-S3 uploads with a hard size cap.

        Returns dict: {
          "url": str,
          "fields": dict,  # send these back to the browser (with the file) as form-data
          "key": str,      # the exact S3 object key
          "max_bytes": int # server-enforced per-upload cap
        }
        """

        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")

        fields = {
            "x-amz-meta-user-id": str(user_id),
            "Content-Type": content_type,
        }

        conditions: list = [
            {"x-amz-meta-user-id": str(user_id)},
            {"Content-Type": content_type},
            ["content-length-range", 0, int(max_bytes)],
        ]

        try:

            presigned = self.s3_client.generate_presigned_post(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=object_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=settings.AWS_PRESIGNED_EXPIRATION_TIME,
            )
        except (NoCredentialsError, ClientError) as e:
            logger.exception(f"Error generating presigned URL: {e}")
            return None

        return {
            "url": presigned["url"],
            "fields": presigned["fields"],  # forward these verbatim to the browser
        }

    def generate_presigned_download_url(
            self, object_name, bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            expiration=settings.AWS_PRESIGNED_EXPIRATION_TIME
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

    def delete_file_from_s3(self, object_name, bucket_name=settings.AWS_STORAGE_BUCKET_NAME):
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
        except Exception as e:
            logger.error(
                "Failed to delete file from S3.",
                extra={
                    "bucket_name": bucket_name,
                    "object_key": object_name,
                    "error": str(e),
                }
            )

            raise Exception("Failed to permanently delete file.")

    def head(self, key: str) -> dict:
        try:
            resp = self.s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            return {
                "size": resp["ContentLength"],
                "content_type": resp.get("ContentType"),
                "metadata": resp.get("Metadata", {}),
            }
        except Exception:
            return None
