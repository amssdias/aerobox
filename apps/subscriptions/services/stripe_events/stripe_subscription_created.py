import logging
from datetime import datetime

from apps.profiles.models import Profile
from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
    SubscriptionBillingCycleChoices,
)
from apps.subscriptions.models import Plan, Subscription
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler


logger = logging.getLogger("aerobox")


class SubscriptionCreateddHandler(StripeEventHandler):
    """
    Handles `customer.subscription.created` event.
    """

    def process(self):
        self.create_subscription()

    def get_user(self):
        customer_id = self.data["customer"]

        try:
            return Profile.objects.get(stripe_customer_id=customer_id).user
        except Profile.DoesNotExist:
            logger.error("Profile does not exist", extra={"stripe_id": customer_id})
            return None

    def get_plan(self):
        stripe_price_id = self.data.plan.id
        try:
            return Plan.objects.get(stripe_price_id=stripe_price_id)
        except Plan.DoesNotExist:
            logger.error(
                "Plan does not exist", extra={"stripe_price_id": stripe_price_id}
            )
            return None

    def create_subscription(self):
        user = self.get_user()
        plan = self.get_plan()
        status = self.get_subscription_status()

        billing_start = datetime.utcfromtimestamp(
            self.data["current_period_start"]
        ).date()
        billing_end = datetime.utcfromtimestamp(self.data["current_period_end"]).date()

        billing_cycle = self.get_billing_cycle()

        Subscription.objects.get_or_create(
            user=user,
            stripe_subscription_id=self.data["id"],
            defaults={
                "plan": plan,
                "billing_cycle": billing_cycle,
                "start_date": billing_start,
                "end_date": billing_end,
                "status": status,
                "trial_start_date": None,
                "is_recurring": True,
            },
        )

    def get_subscription_status(self):
        if self.data.status == "incomplete":
            return SubscriptionStatusChoices.INACTIVE
        elif self.data.status == "active":
            return SubscriptionStatusChoices.ACTIVE

    def get_billing_cycle(self):
        billing_cycle = self.data["items"]["data"][0]["plan"]["interval"]
        if billing_cycle in SubscriptionBillingCycleChoices.values:
            return SubscriptionBillingCycleChoices(billing_cycle).value
        return None
