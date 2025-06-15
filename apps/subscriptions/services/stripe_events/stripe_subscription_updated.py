from apps.subscriptions.services.stripe_events.stripe_subscription_created import SubscriptionCreateddHandler
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.subscription_mixin import StripeSubscriptionMixin


class SubscriptionUpdateddHandler(StripeEventHandler, StripeSubscriptionMixin):
    """
    Handles `customer.subscription.updated` event.
    """

    def process(self):
        self.update_subscription()

    def update_subscription(self):
        stripe_subscription = self.get_stripe_subscription(stripe_subscription_id=self.data.get("id"))
        subscription = self.get_or_create_subscription()
        status = self.get_subscription_status(stripe_subscription.status)

        if subscription.status != status:
            subscription.status = status
            subscription.save()

    def get_or_create_subscription(self):
        stripe_subscription_id = self.data["id"]
        subscription = self.get_subscription(stripe_subscription_id)
        return subscription or SubscriptionCreateddHandler(event=self.event).create_subscription(stripe_subscription_id)
