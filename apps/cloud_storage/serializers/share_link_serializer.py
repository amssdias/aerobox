from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import serializers

from apps.cloud_storage.models import ShareLink, CloudFile, Folder


class ShareLinkSerializer(serializers.ModelSerializer):
    files = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CloudFile.not_deleted.all(),
        required=False,
    )
    folders = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Folder.objects.filter(parent__isnull=True),
        required=False,
    )

    class Meta:
        model = ShareLink
        fields = (
            "id",
            "token",
            "files",
            "folders",
            "expires_at",
            "password",
            "revoked_at",
            "created_at",
        )
        read_only_fields = ("id", "token", "created_at", "updated_at", "revoked_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["files"] = [
            {"id": f.id, "name": f.file_name} for f in instance.files.all()
        ]
        return data

    def validate(self, data):
        files = data.get("files")
        folders = data.get("folders")
        if not files and not folders and not self.instance:
            raise serializers.ValidationError(
                "A share link must include at least one file or folder."
            )

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        file_sharing_config = user.file_sharing_config

        validated_data["expires_at"] = self.expiration_normalization(
            file_sharing_config, validated_data
        )

        raw_password = validated_data.pop("password", None)
        if raw_password:
            validated_data["password"] = make_password(raw_password)

        validated_data["owner"] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        file_sharing_config = user.file_sharing_config

        expires_at = (
            validated_data.get("expires_at")
            if file_sharing_config.get("allow_choose_expiration", False)
            else instance.expires_at
        )
        validated_data["expires_at"] = expires_at

        instance.set_password(validated_data.pop("password", None))

        return super().update(instance, validated_data)

    @staticmethod
    def expiration_normalization(file_sharing_config, validated_data):
        expires_at = validated_data.get("expires_at")
        if (
                not file_sharing_config.get("allow_choose_expiration", False)
                or not expires_at
        ):
            max_exp_minutes = file_sharing_config.get(
                "max_expiration_minutes",
                settings.DEFAULT_SHARELINK_EXPIRATION_MINUTES,
            )
            expires_at = timezone.now() + timedelta(minutes=max_exp_minutes)

        return expires_at
