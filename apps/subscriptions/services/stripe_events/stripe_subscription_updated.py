import logging

from apps.subscriptions.models import Plan
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.subscription_mixin import StripeSubscriptionMixin

logger = logging.getLogger("aerobox")


class SubscriptionUpdatedHandler(StripeEventHandler, StripeSubscriptionMixin):
    """
    Handles `customer.subscription.updated` event.
    """

    def process(self):
        subscription_id = self.data["id"]
        previous_attributes = self.event["data"].get("previous_attributes", {})

        self.update_subscription(subscription_id, previous_attributes)

    def update_subscription(self, subscription_id, previous_attributes):
        subscription = self.get_subscription(stripe_subscription_id=subscription_id)
        stripe_subscription = self.get_stripe_subscription(
            stripe_subscription_id=subscription.stripe_subscription_id) if subscription else None

        plan_id = previous_attributes and previous_attributes.get("plan", {}).get("id")
        # Change from one subscription to another one
        if plan_id and subscription and subscription.plan.stripe_price_id == plan_id:
            self.change_plan_subscription(subscription, stripe_subscription)

        if stripe_subscription and stripe_subscription.cancel_at_period_end:
            self.cancel_subscription(subscription)

    def change_plan_subscription(self, subscription, stripe_subscription):
        new_plan = self.get_plan(stripe_subscription.plan.get("id"))
        if new_plan:
            subscription.plan = new_plan
            subscription.save(update_fields=["plan"])

    @staticmethod
    def cancel_subscription(subscription):
        subscription.is_recurring = False
        subscription.save(update_fields=["is_recurring"])

    @staticmethod
    def get_plan(plan_stripe_price_id):
        try:
            return Plan.objects.get(stripe_price_id=plan_stripe_price_id, is_free=False)

        except Plan.DoesNotExist:
            logger.critical(
                "No plan found for the given Stripe price ID.", extra={"stripe_price_id": plan_stripe_price_id}
            )
        except Plan.MultipleObjectsReturned:
            logger.critical(
                "Multiple plans found with the same Stripe price ID. Expected only one.",
                extra={"stripe_price_id": plan_stripe_price_id}
            )

        return None
