import logging
from datetime import datetime

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
)
from apps.subscriptions.models import Subscription
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler

logger = logging.getLogger("aerobox")


class SubscriptionDeleteddHandler(StripeEventHandler):
    """
    Handles `customer.subscription.deleted` event.
    """

    def process(self):
        subscription_id = self.data["id"]
        ended_at = self.data.get("ended_at", None)

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)

            subscription.status = SubscriptionStatusChoices.CANCELED.value
            subscription.end_date = datetime.utcfromtimestamp(ended_at).date() if ended_at else subscription.end_date
            subscription.save()

        except Subscription.DoesNotExist:
            logger.error("Subscription does not exist", extra={"stripe_subscription_id": subscription_id})
