import logging

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
)
from apps.subscriptions.models import Subscription
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler

logger = logging.getLogger("aerobox")


class SubscriptionUpdateddHandler(StripeEventHandler):
    """
    Handles `customer.subscription.updated` event.
    """

    def process(self):
        self.update_subscription()

    def update_subscription(self):
        subscription_id = self.data["id"]

        subscription = self.get_subscription(subscription_id)
        status = self.get_subscription_status()

        if not subscription or not status:
            return False

        subscription.status = status
        subscription.save()

    @staticmethod
    def get_subscription(subscription_id):
        try:
            return Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            logger.error(
                "Subscription not found: The provided Stripe subscription ID does not exist.",
                extra={"stripe_subscription_id": subscription_id},
            )

    def get_subscription_status(self):
        if "status" not in self.data:
            return None
        if self.data["status"] == "incomplete":
            return SubscriptionStatusChoices.INACTIVE.value
        elif self.data["status"] == "active":
            return SubscriptionStatusChoices.ACTIVE.value
