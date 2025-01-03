import mimetypes

from apps.cloud_storage.constants.cloud_files import USER_PREFIX
from apps.cloud_storage.models import CloudFile
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class CloudFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFile
        fields = (
            "file_name",
            "path",
            "size",
            "content_type",
            "checksum",
            "file_url",
        )

    def validate_file_name(self, value):
        """
        Ensure the file_name does not start with unsafe characters like '/'.
        """
        if "/" in value or "\\" in value:
            raise serializers.ValidationError(_("The file name cannot contain '/' or '\\'."))
        if not value.strip():
            raise serializers.ValidationError(_("The file name cannot be empty or consist only of whitespace."))
        return value

    def validate_path(self, value):
        """
        Construct the full path dynamically during validation.
        """
        user = self.context["request"].user

        # Base prefix
        user_prefix = USER_PREFIX.format(user.id)
        folder_path = value.strip() if value else ""

        if folder_path.startswith("/") or folder_path.startswith("\\"):
            raise serializers.ValidationError(_("The file path cannot start with '/' or '\\'."))
        if folder_path.endswith("/") or folder_path.endswith("\\"):
            raise serializers.ValidationError(_("The file path cannot end with '/' or '\\'."))

        file_name = self.initial_data.get("file_name")

        if folder_path:
            full_path = f"{user_prefix}{folder_path}/{file_name}".strip("/")
        else:
            full_path = f"{user_prefix}{file_name}".strip("/")

        return full_path

    def validate(self, data):
        user = self.context["request"].user
        if not user:
            raise serializers.ValidationError(_("User is not authenticated."))

        file_name = data.get("file_name")
        content_type, _encoding_type = mimetypes.guess_type(file_name)
        if content_type != data.get("content_type"):
            raise serializers.ValidationError(_("Content type sent is not correct."))

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user

        file_name = validated_data.get("file_name")
        validated_data["content_type"], _encoding_type = mimetypes.guess_type(file_name)
        return super().create(validated_data)
