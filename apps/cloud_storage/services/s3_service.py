from botocore.exceptions import NoCredentialsError, ClientError

from .aws_client import AWSClient


class S3Service:
    def __init__(self):
        self.s3_client = AWSClient("s3").get_client()

    def generate_presigned_upload_url(self, bucket_name, object_name, expiration=3600):
        """
        Generates a presigned URL for uploading a file to S3.

        :param bucket_name: Name of the S3 bucket
        :param object_name: S3 key (object path) where the file will be stored
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as a string or None if there is an error
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expiration,
                HttpMethod="PUT"
            )
            return presigned_url
        except (NoCredentialsError, ClientError) as e:
            print(f"Error generating presigned URL: {e}")
            return None
