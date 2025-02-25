import logging

import stripe
from django.conf import settings

from apps.subscriptions.services.stripe_events.stripe_subscription import (
    SubscriptiondHandler,
)
from apps.subscriptions.services.stripe_events.stripe_subscription_deleted import SubscriptionDeleteddHandler

logger = logging.getLogger("aerobox")


class StripeService:
    """
    A service class for handling Stripe operations.
    """

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def process_webhook_event(self, event):
        """
        Routes Stripe events to the correct handler.
        """
        event_type = event["type"]
        handler = self.get_handler(event_type, event)

        if handler:
            handler.process()
        else:
            logger.error(f"Unhandled event type: {event}")

    @staticmethod
    def get_handler(event_type, event):
        """
        Returns the correct event handler based on the event type.
        """
        handlers = {
            "customer.subscription.created": SubscriptiondHandler,
            "customer.subscription.deleted": SubscriptionDeleteddHandler,
        }
        return handlers.get(event_type, None)(event) if event_type in handlers else None
