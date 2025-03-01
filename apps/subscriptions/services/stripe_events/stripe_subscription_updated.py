from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
)
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.customer_event import StripeCustomerMixin


class SubscriptionUpdateddHandler(StripeEventHandler, StripeCustomerMixin):
    """
    Handles `customer.subscription.updated` event.
    """

    def process(self):
        self.update_subscription()

    def update_subscription(self):
        subscription_id = self.data["id"]

        subscription = self.get_subscription(subscription_id)
        status = self.get_subscription_status()

        if self.can_update(subscription, subscription_id, status):
            subscription.status = status
            subscription.save()

    def get_subscription_status(self):
        if "status" not in self.data:
            return None
        if self.data["status"] == "incomplete":
            return SubscriptionStatusChoices.INACTIVE.value
        elif self.data["status"] == "active":
            return SubscriptionStatusChoices.ACTIVE.value

    def can_update(self, subscription, subscription_id, status):
        if not subscription:
            raise ValueError(f"Subscription with Stripe ID '{subscription_id}' not found.")
        if not status:
            raise ValueError(f"Subscription status missing in Stripe event: {self.data}")

        return True
