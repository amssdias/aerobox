from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.features.choices.feature_code_choices import FeatureCodeChoices


class FolderParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "name"]


class FolderSerializer(serializers.ModelSerializer):
    parent = FolderParentSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        source='parent',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "parent_id", "user", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "parent", "created_at", "updated_at", ]

    def validate(self, attrs):
        user = self.context["request"].user
        parent = attrs.get("parent")
        name = attrs.get("name", self.instance.name if self.instance else None)

        if Folder.objects.filter(user=user, parent=parent, name__iexact=name).exclude(
                pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError(_("A folder with this name already exists in the same parent folder."))

        self.validate_user_subscription()
        return attrs

    def validate_user_subscription(self):
        user = self.context["request"].user

        subscription = user.subscriptions.filter(status="active").first()
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
