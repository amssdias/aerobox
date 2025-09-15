from django.utils.translation import gettext_lazy as _
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


class ChangePlanSerializer(serializers.Serializer):
    target_plan = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True).only("id"),
        help_text="ID of the target plan"
    )

    def validate_target_plan(self, data):
        current_plan = self.context.get("current_plan")

        if current_plan.id == data.id:
            raise serializers.ValidationError(_("You are already subscribed to this plan."))

        if current_plan.monthly_price < data.monthly_price:
            raise serializers.ValidationError(
                _("Upgrading to a higher plan is not available yet. Please try again later."))

        if not data.stripe_price_id and not data.is_free:
            raise serializers.ValidationError(
                _("This plan is not available for subscription at the moment. Please choose another plan."))

        return data
