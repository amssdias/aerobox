import logging
import mimetypes

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from apps.cloud_storage.choices.cloud_file_error_code_choices import CloudFileErrorCode
from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED
from apps.cloud_storage.models import CloudFile, Folder
from apps.cloud_storage.services.storage.s3_service import S3Service
from apps.cloud_storage.utils.path_utils import build_object_path
from apps.cloud_storage.utils.size_utils import get_user_used_bytes

logger = logging.getLogger("aerobox")

S3_TO_INTERNAL_CODES = {
    "EntityTooLarge": "file_too_large",
}


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
            "deleted_at",
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

    def validate_size(self, value):
        """
        Validate that the user has enough available storage space
        for the file being uploaded, based on their target plan.
        """

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError(_("Invalid context: user not provided or not authenticated."))

        subscription = user.active_subscription
        if not subscription:
            raise serializers.ValidationError(_("No active subscription found for this user."))

        plan = subscription.plan
        if not plan:
            raise serializers.ValidationError(_("No plan associated with the active subscription."))

        max_file_upload_size_bytes = plan.max_file_upload_size_bytes
        if value > max_file_upload_size_bytes:
            BYTES_IN_MB = 1_000_000
            limit_mb = max_file_upload_size_bytes / BYTES_IN_MB
            given_mb = value / BYTES_IN_MB

            raise serializers.ValidationError(
                _(
                    "This file is too large. "
                    "Your plan allows files up to %(limit).0f MB (this one is %(given).2f MB)."
                ) % {"limit": limit_mb, "given": given_mb}
            )

        limit_bytes = plan.max_storage_bytes
        used_bytes = get_user_used_bytes(user)

        # Check against plan limit
        if limit_bytes is not None and (used_bytes + value > limit_bytes):
            raise serializers.ValidationError(
                f"Upload exceeds your plan’s storage limit."
            )

        return value

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


class CloudFileMetaPatchSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(required=True, choices=[SUCCESS, FAILED])
    error_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CloudFile
        fields = ("status", "error_code", "error_message")

    def validate_error_code(self, value):
        return S3_TO_INTERNAL_CODES.get(value, CloudFileErrorCode.UNKNOWN_S3_ERROR)

    def validate(self, data):
        is_status_success = data.get("status") == SUCCESS

        if is_status_success:
            data["error_code"] = None
            return data

        error_code = data.get("error_code")
        data["error_code"] = data.get("error_code", CloudFileErrorCode.UNKNOWN_S3_ERROR) if error_code else None
        return data

class CloudFileUpdateSerializer(serializers.ModelSerializer):
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

    def update(self, instance, validated_data):
        new_name = validated_data.pop("file_name", None)
        if new_name:
            old_extension = instance.file_name.split(".")[-1]
            instance.file_name = f"{new_name}.{old_extension}"

        instance = super().update(instance, validated_data)

        instance.rebuild_path()
        instance.save()

        return instance
