import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.cloud_storage.tasks.file_path_updates import update_folder_file_paths_task
from apps.features.choices.feature_code_choices import FeatureCodeChoices


class FolderParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class FolderSerializer(serializers.ModelSerializer):
    parent = FolderParentSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        source='parent',
        write_only=True,
        required=False,
        allow_null=True
    )
    subfolders_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "parent_id", "user", "created_at", "updated_at", "subfolders_count",
                  "files_count"]
        read_only_fields = ["id", "user", "parent", "created_at", "updated_at", "subfolders_count", "files_count"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user = self.context.get("user")

        if user is None:
            user = self.context["request"].user
        self.fields["parent_id"].queryset = Folder.objects.filter(user=user)

    def validate_name(self, value):
        # Reject paths that contain backslashes `\`
        if "\\" in value:
            raise serializers.ValidationError(
                _("The file path must use '/' instead of '\\'.")
            )

        # Ensure the path does NOT start or end with a slash
        if value.startswith("/") or value.endswith("/"):
            raise serializers.ValidationError(
                _("The file path cannot start or end with '/'.")
            )

        # Ensure the path does NOT contain consecutive slashes (e.g., "folder1////folder2")
        if re.search(r"//+", value):
            raise serializers.ValidationError(
                _("The file path cannot contain consecutive slashes.")
            )

        return value

    def validate(self, attrs):
        user = self.context["request"].user
        parent = attrs.get("parent")
        name = attrs.get("name", self.instance.name if self.instance else None)

        if Folder.objects.filter(user=user, parent=parent, name__iexact=name).exclude(
                pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(_("A folder with this name already exists in the same parent folder."))

        self.validate_user_subscription()
        return attrs

    def validate_user_subscription(self):
        user = self.context["request"].user

        subscription = user.active_subscription
        if not subscription:
            raise serializers.ValidationError(
                _("You need an active subscription to use this feature. Please check your billing or subscribe to a plan."))

        create_folder_feature = subscription.plan.features.filter(code=FeatureCodeChoices.FOLDER_CREATION)
        if not create_folder_feature:
            raise serializers.ValidationError(
                _("Your current subscription plan does not include the folder creation feature. "
                  "Please upgrade your plan to access this functionality.")
            )

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_name = instance.name
        old_parent_id = instance.parent_id

        updated_folder = super().update(instance, validated_data)

        name_changed = "name" in validated_data and validated_data["name"] != old_name
        parent_changed = "parent" in validated_data and updated_folder.parent_id != old_parent_id

        if name_changed or parent_changed:
            update_folder_file_paths_task.delay(updated_folder.id)

        return updated_folder

    def get_subfolders_count(self, obj):
        return obj.subfolders.all().count()

    def get_files_count(self, obj):
        return obj.files.all().count()

class FolderDetailSerializer(serializers.ModelSerializer):
    parent = FolderParentSerializer(read_only=True)
    subfolders = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "subfolders", "files"]

    def get_subfolders(self, obj):
        return FolderSerializer(obj.subfolders.all(), many=True, context=self.context).data

    def get_files(self, obj):
        return CloudFilesSerializer(obj.files.all(), many=True, context=self.context).data
