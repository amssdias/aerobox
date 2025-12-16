from rest_framework import serializers

from apps.cloud_storage.models import ShareLink, Folder
from apps.cloud_storage.serializers import CloudFilesSerializer, FolderParentSerializer
from apps.cloud_storage.serializers.folder_serializer import SimpleFolderSerializer


class PublicShareLinkDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    is_password_protected = serializers.SerializerMethodField()
    files = CloudFilesSerializer(many=True, read_only=True)
    folders = FolderParentSerializer(many=True, read_only=True)

    class Meta:
        model = ShareLink
        fields = (
            "token",
            "owner_name",
            "expires_at",
            "created_at",
            "is_password_protected",
            "files",
            "folders",
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


class ShareLinkPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )


class PublicShareFolderDetailSerializer(serializers.ModelSerializer):
    parent = FolderParentSerializer(read_only=True)
    subfolders = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "subfolders", "files"]

    def get_subfolders(self, obj):
        return SimpleFolderSerializer(obj.subfolders.all(), many=True).data

    def get_files(self, obj):
        return CloudFilesSerializer(obj.files.all(), many=True).data
