from apps.cloud_storage.models import CloudFiles
from rest_framework import serializers


class CloudFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFiles
        fields = (
            "name",
            "path",
            "size",
            "file_type",
            "user",
            "status",
            "checksum",
            "file_url",
        )
