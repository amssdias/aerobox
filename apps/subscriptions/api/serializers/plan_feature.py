from rest_framework import serializers

from apps.subscriptions.models import PlanFeature


class FeaturePlanSerializer(serializers.ModelSerializer):
    name = serializers.JSONField(source="feature.name")
    description = serializers.JSONField(source="feature.description")
    code = serializers.CharField(source="feature.code")
    default_metadata = serializers.JSONField(source="feature.metadata")
    metadata = serializers.JSONField()

    class Meta:
        model = PlanFeature
        fields = ["code", "name", "description", "metadata", "default_metadata"]
