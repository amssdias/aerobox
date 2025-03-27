from rest_framework import serializers

from apps.subscriptions.models import PlanFeature


class FeaturePlanSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="feature.name")  # Pull from Feature model
    description = serializers.CharField(source="feature.description")
    code = serializers.CharField(source="feature.code")
    default_metadata = serializers.JSONField(source="feature.metadata")
    metadata = serializers.JSONField()

    class Meta:
        model = PlanFeature
        fields = ["code", "name", "description", "metadata", "default_metadata"]
