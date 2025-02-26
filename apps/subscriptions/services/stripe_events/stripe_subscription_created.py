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

        try:
            customer_id = self.data["customer"]
            return Profile.objects.get(stripe_customer_id=customer_id).user

        except Profile.DoesNotExist:
            logger.error("No profile found for the given Stripe customer ID.", extra={"stripe_id": customer_id})
        except KeyError:
            logger.error("Missing 'customer' key in Stripe event data.", extra={"stripe_data": self.data})
        return None

    def get_plan(self):
        try:
            stripe_price_id = self.data["plan"]["id"]
            return Plan.objects.get(stripe_price_id=stripe_price_id)

        except Plan.DoesNotExist:
            logger.error(
                "No plan found for the given Stripe price ID.", extra={"stripe_price_id": stripe_price_id}
            )
        except KeyError:
            logger.error("Missing 'id' key under 'plan' in Stripe event data.", extra={"stripe_data": self.data})

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

        if not user or not plan or not status or not billing_start or not billing_end or not billing_cycle:
            return False

        obj, created = Subscription.objects.get_or_create(
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

        if created:
            return True

    def get_subscription_status(self):
        data_status = self.data["status"]
        if data_status == "incomplete":
            return SubscriptionStatusChoices.INACTIVE.value
        elif data_status == "active":
            return SubscriptionStatusChoices.ACTIVE.value

    def get_billing_cycle(self):
        billing_cycle = self.data["items"]["data"][0]["plan"]["interval"]
        if billing_cycle in SubscriptionBillingCycleChoices.values:
            return SubscriptionBillingCycleChoices(billing_cycle).value
        return None
