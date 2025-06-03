import logging
import mimetypes

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from apps.cloud_storage.models import CloudFile, Folder
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_object_path

logger = logging.getLogger("aerobox")


class CloudFilesSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
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
            "path",
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

        if value.startswith(".") or value.endswith("."):
            raise serializers.ValidationError(
                _("The file name cannot start or end with a '.'.")
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

        validated_data["path"] = build_object_path(
            file_name=file_name,
            folder=validated_data.get("folder"),
        )

        return super().create(validated_data)

    def get_url(self, obj):
        """Only add extra_info when retrieving a single object"""
        if self.context.get("is_detail", False):
            s3_service = S3Service()

            try:
                download_url = s3_service.generate_presigned_download_url(
                    object_name=obj.s3_key
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
    file_name = serializers.CharField(
        required=False,
        max_length=255,
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = CloudFile
        fields = ("file_name", "folder")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        self.fields["folder"].queryset = Folder.objects.filter(user=user)

    def validate_file_name(self, value):
        if "/" in value or "\\" in value:
            raise serializers.ValidationError(
                _("The file name cannot contain '/' or '\\'.")
            )

        if value.startswith(".") or value.endswith("."):
            raise serializers.ValidationError(
                _("The file name cannot start or end with a '.'.")
            )

        if not value.strip():
            raise serializers.ValidationError(
                _("The file name cannot be empty or consist only of whitespace.")
            )
        return value.lower()

    def validate(self, attrs):
        if not attrs.get("file_name") and not attrs.get("folder"):
            raise serializers.ValidationError("You must provide either file_name or folder.")
        return attrs

    def update(self, instance, validated_data):
        new_name = validated_data.pop("file_name", None)
        if new_name:
            old_extension = instance.file_name.split(".")[-1]
            instance.file_name = f"{new_name}.{old_extension}"

        instance = super().update(instance, validated_data)

        instance.rebuild_path()
        instance.save()

        return instance
