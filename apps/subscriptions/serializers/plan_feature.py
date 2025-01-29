from rest_framework import serializers

from apps.subscriptions.models import PlanFeature


class FeaturePlanSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="feature.name")  # Pull from Feature model
    description = serializers.CharField(source="feature.description")
    metadata = serializers.JSONField()

    class Meta:
        model = PlanFeature
        fields = ["name", "description", "metadata"]
