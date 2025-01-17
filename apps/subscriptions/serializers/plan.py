from rest_framework import serializers

from apps.subscriptions.models import Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "description", "monthly_price", "yearly_price", "storage_limit"]
