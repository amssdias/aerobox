import logging
import mimetypes
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_s3_path

logger = logging.getLogger(__name__)


class CloudFilesSerializer(serializers.ModelSerializer):
    relative_path = serializers.SerializerMethodField()
    path = serializers.CharField(write_only=True, allow_blank=True)
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CloudFile
        fields = (
            "id",
            "file_name",
            "path",
            "size",
            "content_type",
            "relative_path",
            "url",
            "created_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if not self.context.get("is_detail", False):
            data.pop("url", None)

        return data

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
        return value.lower()

    def validate_path(self, value):
        """
        Validates the file path:
        - Allows an empty string `""` for the root path.
        - Ensures only forward slashes `/`, no leading/trailing slashes, and no consecutive slashes.
        - Rejects paths that contain dots (`.`) to prevent incorrect file names.
        """
        user = self.context["request"].user

        folder_path = value.strip().lower()

        # Get file name from request data
        file_name = self.initial_data.get("file_name")

        # Allow empty path (interpreted as root)
        if not folder_path:
            full_path = build_s3_path(user.id, file_name)
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

            # Reject paths that contain dots (`.`), ensuring only file names can have extensions
            if "." in folder_path:
                raise serializers.ValidationError(
                    _(
                        "The file path cannot contain dots (`.`). Dots are only allowed in file names for extensions."
                    )
                )

            # Construct the full path
            full_path = build_s3_path(user.id, f"{folder_path}/{file_name}")

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

    def get_url(self, obj):
        """Only add extra_info when retrieving a single object"""
        if self.context.get("is_detail", False):
            s3_service = S3Service()

            try:
                download_url = s3_service.generate_presigned_download_url(
                    object_name=obj.path
                )
                if not download_url:
                    raise serializers.ValidationError(
                        _(
                            "Unable to generate download URL. The file may not exist or there was an error with the storage service."
                        )
                    )
                return download_url

            except Exception as e:
                logger.error(
                    f"Error generating presigned URL for file '{obj.path}': {str(e)}",
                    exc_info=True,
                )
                raise serializers.ValidationError(
                    _("Failed to retrieve file. Please try again later.")
                )

        return None


class CloudFileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFile
        fields = ("status", "error_message")
