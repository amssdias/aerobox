import mimetypes
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.cloud_storage.constants.cloud_files import USER_PREFIX
from apps.cloud_storage.models import CloudFile


class CloudFilesSerializer(serializers.ModelSerializer):
    relative_path = serializers.SerializerMethodField()
    path = serializers.CharField(write_only=True, allow_blank=True)

    class Meta:
        model = CloudFile
        fields = (
            "id",
            "file_name",
            "path",
            "size",
            "content_type",
            "relative_path",
        )

    def validate_file_name(self, value):
        """
        Ensure the file_name does not start with unsafe characters like '/'.
        """
        if "/" in value or "\\" in value:
            raise serializers.ValidationError(
                _("The file name cannot contain '/' or '\\'.")
            )
        if not value.strip():
            raise serializers.ValidationError(
                _("The file name cannot be empty or consist only of whitespace.")
            )
        return value

    def validate_path(self, value):
        """
        Validates the file path:
        - Allows an empty string `""` for the root path.
        - Ensures only forward slashes `/`, no leading/trailing slashes, and no consecutive slashes.
        """
        user = self.context["request"].user

        # Base prefix for user
        user_prefix = USER_PREFIX.format(user.id)

        folder_path = value.strip()

        # Get file name from request data
        file_name = self.initial_data.get("file_name")

        # Allow empty path (interpreted as root)
        if not folder_path:
            full_path = f"{user_prefix}/{file_name}".strip("/")
        else:
            # Reject paths that contain backslashes `\`
            if "\\" in folder_path:
                raise serializers.ValidationError(
                    _("The file path must use '/' instead of '\\'.")
                )

            # Ensure the path does NOT start or end with a slash
            if folder_path.startswith("/") or folder_path.endswith("/"):
                raise serializers.ValidationError(
                    _("The file path cannot start or end with '/'.")
                )

            # Ensure the path does NOT contain consecutive slashes (e.g., "folder1////folder2")
            if re.search(r"//+", folder_path):
                raise serializers.ValidationError(
                    _("The file path cannot contain consecutive slashes.")
                )

            # Construct the full path
            full_path = f"{user_prefix}/{folder_path}/{file_name}".strip("/")

        if CloudFile.objects.filter(path=full_path).exists():
            raise serializers.ValidationError("A file with this name already exists.")

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

    def get_relative_path(self, obj):
        return obj.get_relative_path()


class CloudFileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFile
        fields = ("status", "error_message")
