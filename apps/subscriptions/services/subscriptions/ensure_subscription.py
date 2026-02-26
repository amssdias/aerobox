import logging

from apps.integrations.stripe.subscriptions.mappers.subscription import to_subscription_summary
from apps.integrations.stripe.subscriptions.subscription import get_stripe_subscription
from apps.subscriptions.services.common import get_subscription
from apps.subscriptions.services.subscriptions.create_subscription import create_subscription

logger = logging.getLogger("aerobox")


def get_or_sync_subscription_from_stripe(stripe_subscription_id):
    subscription = get_subscription(stripe_subscription_id)
    return subscription if subscription else create_subscription_from_stripe(stripe_subscription_id)


def create_subscription_from_stripe(stripe_subscription_id):
    try:
        stripe_sub = get_stripe_subscription(stripe_subscription_id)
        subscription_summary = to_subscription_summary(stripe_sub)
        return create_subscription(subscription_summary)
    except Exception as exc:
        logger.exception(
            "Subscription not created from stripe.",
            extra={"stripe_subscription_id": stripe_subscription_id},
        )
        raise
