import logging
import mimetypes

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from apps.cloud_storage.models import CloudFile, Folder
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_s3_object_path

logger = logging.getLogger("aerobox")


class CloudFilesSerializer(serializers.ModelSerializer):
    relative_path = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField(read_only=True)
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = CloudFile
        fields = (
            "id",
            "file_name",
            "folder",
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

    def validate_folder(self, folder):
        if folder and folder.user != self.context["request"].user:
            raise serializers.ValidationError(
                _("You don’t have permission to upload files to this folder. Please select one of your own folders.")
            )
        return folder

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

        validated_data["path"] = build_s3_object_path(
            user=user,
            file_name=file_name,
            folder=validated_data.get("folder"),
        )

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

            except Exception as e:
                logger.error(
                    f"Error generating presigned URL for file '{obj.path}': {str(e)}",
                    exc_info=True,
                )
                raise serializers.ValidationError(
                    _("Failed to retrieve file. Please try again later.")
                )

            if not download_url:
                raise NotFound(
                    _(
                        "Unable to generate download URL. The file may not exist or there was an error with the storage service."
                    )
                )
            return download_url

        return None


class CloudFileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFile
        fields = ("status", "error_message")


class RenameFileSerializer(serializers.ModelSerializer):
    """Serializer for renaming a file."""
    file_name = serializers.CharField(required=True, max_length=255,)
    path = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CloudFile
        fields = ("file_name", "path")

    def validate_file_name(self, value):
        """
        Ensure the file_name does not start with unsafe characters like '/'.
        """
        if "/" in value or "\\" in value:
            raise serializers.ValidationError(
                _("The file name cannot contain '/' or '\\'.")
            )
        if "." in value:
            raise serializers.ValidationError(
                _("The file name cannot contain '.' or extensions.")
            )

        if self.instance.file_name.split(".")[0] == value:
            raise serializers.ValidationError(
                _("The new file name cannot be the same as the current file name.")
            )

        if not value.strip():
            raise serializers.ValidationError(
                _("The file name cannot be empty or consist only of whitespace.")
            )
        return value.lower()

    def update(self, instance, validated_data):
        """
        Handles renaming the file in S3 and updating the database.
        """

        old_file_name = instance.file_name
        old_path = instance.path
        file_extension = old_file_name.split(".")[-1]
        new_name = validated_data.get("file_name")
        new_file_name = f"{new_name}.{file_extension}"

        instance.file_name = new_file_name
        instance.path = instance.path.replace(old_file_name, new_file_name)

        s3_service = S3Service()

        # Rename the file in S3
        if not s3_service.rename_file(old_path, instance.path):
            raise serializers.ValidationError({"error": "S3 rename operation failed."})

        # Update database record
        instance.save()

        return instance
