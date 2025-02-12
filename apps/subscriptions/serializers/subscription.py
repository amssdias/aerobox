import logging

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.payments.services.stripe_api import create_stripe_checkout_session
from apps.subscriptions.choices.subscription_choices import SubscriptionBillingCycleChoices
from apps.subscriptions.models import Subscription, Plan

logger = logging.getLogger("aerobox")


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


class CheckoutSubscriptionSerializer(serializers.Serializer):

    plan = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), required=True
    )
    billing_cycle = serializers.ChoiceField(
        choices=SubscriptionBillingCycleChoices.choices, required=True
    )

    def validate_plan(self, plan):
        """Ensure the selected plan has a valid `stripe_price_id`."""
        if not plan.stripe_price_id:
            logger.error(
                "Plan does not have a Stripe price ID.", extra={"plan_id": plan.id}
            )

            raise serializers.ValidationError(
                _("This plan is currently unavailable for purchase.")
            )
        return plan

    def validate(self, data):
        billing_cycle = data.get("billing_cycle")
        plan = data.get("plan")

        amount = plan.monthly_price if billing_cycle == "monthly" else plan.yearly_price
        if not amount:
            raise serializers.ValidationError(_("Sorry, no amount defined for this plan."))

        return data

    def get_checkout_session_url(self, user):
        plan = self.validated_data["plan"]

        # Call Stripe API service
        checkout_url = create_stripe_checkout_session(plan)

        return {"checkout_url": checkout_url}
