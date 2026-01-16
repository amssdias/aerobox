import boto3
from django.conf import settings


class AWSClient:
    _instances = {}

    def __new__(cls, service_name, *args, **kwargs):
        """
        Implement the singleton pattern for the AWS client,
        making sure only one instance per service is created.
        """
        if service_name not in cls._instances:
            cls._instances[service_name] = super(AWSClient, cls).__new__(cls)
            cls._instances[service_name]._init_client(service_name)
        return cls._instances[service_name]

    def _init_client(self, service_name):
        """
        Initialize the boto3 client for the given AWS service.
        This method is called only once per service.
        """
        self.client = boto3.client(
            service_name,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_BUCKET_REGION
        )

    def get_client(self):
        """
        Return the initialized boto3 client.
        """
        return self.client
