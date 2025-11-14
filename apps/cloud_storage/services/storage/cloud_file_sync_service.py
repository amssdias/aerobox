from .s3_service import S3Service


class CloudFileSyncService:

    def __init__(self):
        self.storage = S3Service()

    def sync(self, cloud_file):
        """Fetch S3 metadata and update the CloudFile instance."""
        s3_meta = self.storage.head(cloud_file.s3_key)

        if not s3_meta:
            return None

        cloud_file.size = s3_meta["size"]
        cloud_file.content_type = s3_meta["content_type"]
        cloud_file.metadata = s3_meta.get("metadata", {})

        cloud_file.save(update_fields=["size", "content_type", "metadata"])

        return cloud_file
