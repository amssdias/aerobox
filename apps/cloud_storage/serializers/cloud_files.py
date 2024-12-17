import mimetypes

from apps.cloud_storage.models import CloudFile
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _



class CloudFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFile
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

    def validate(self, data):
        user = self.context["request"].user
        if not user:
            raise serializers.ValidationError(_("User is not authenticated."))

        file_name = data.get("file_name")
        content_type = mimetypes.guess_type(file_name)
        if content_type != data.get("file_type"):
            raise serializers.ValidationError(_("Content type sent is not correct."))

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user

        file_name = validated_data.get("file_name")
        validated_data["file_type"] = mimetypes.guess_type(file_name)
        return super().create(validated_data)
