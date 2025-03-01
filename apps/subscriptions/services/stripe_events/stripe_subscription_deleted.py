import logging
from datetime import datetime

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
)
from apps.subscriptions.models import Subscription
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.customer_event import StripeCustomerMixin

logger = logging.getLogger("aerobox")


class SubscriptionDeleteddHandler(StripeEventHandler, StripeCustomerMixin):
    """
    Handles `customer.subscription.deleted` event.
    """

    def process(self):
        subscription_id = self.data["id"]
        subscription = self.get_subscription(subscription_id=subscription_id)

        if not subscription:
            return

        ended_at = self.data.get("ended_at", None)
        self.update_subscription(subscription, ended_at)

    @staticmethod
    def update_subscription(subscription, ended_at):
        subscription.status = SubscriptionStatusChoices.CANCELED.value
        subscription.end_date = datetime.utcfromtimestamp(ended_at).date() if ended_at else subscription.end_date
        subscription.save()
