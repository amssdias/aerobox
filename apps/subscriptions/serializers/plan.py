from rest_framework import serializers

from apps.subscriptions.models import Plan
from apps.subscriptions.serializers.plan_feature import FeaturePlanSerializer


class PlanSerializer(serializers.ModelSerializer):
    features = FeaturePlanSerializer(source="plan_features", many=True)

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "monthly_price",
            "yearly_price",
            "features",
        ]
