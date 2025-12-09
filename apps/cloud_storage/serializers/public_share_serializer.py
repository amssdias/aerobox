from rest_framework import serializers

from apps.cloud_storage.models import ShareLink
from apps.cloud_storage.serializers import CloudFilesSerializer, FolderDetailSerializer


class PublicShareLinkMetaSerializer(serializers.ModelSerializer):
    """
    Used when we only want to expose metadata about the link,
    e.g. before password validation.
    """

    owner_name = serializers.SerializerMethodField()
    is_password_protected = serializers.SerializerMethodField()

    class Meta:
        model = ShareLink
        fields = (
            "token",
            "owner_name",
            "expires_at",
            "created_at",
            "is_password_protected",
        )
        read_only_fields = fields

    def get_owner_name(self, obj):
        user = obj.owner
        if not user:
            return None
        return getattr(user, "get_full_name", lambda: None)() or getattr(
            user, "username", None
        )

    def get_is_password_protected(self, obj):
        return bool(obj.password)


class PublicShareLinkDetailSerializer(PublicShareLinkMetaSerializer):
    """
    Used when the link is accessible (no password or password already validated).
    Includes the shared files and folders.
    """

    files = CloudFilesSerializer(many=True, read_only=True)
    folders = FolderDetailSerializer(many=True, read_only=True)

    class Meta(PublicShareLinkMetaSerializer.Meta):
        fields = PublicShareLinkMetaSerializer.Meta.fields + (
            "files",
            "folders",
        )
