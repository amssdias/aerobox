import logging

from apps.subscriptions.models import Subscription

logger = logging.getLogger("aerobox")


def get_subscription(stripe_subscription_id):
    try:
        return Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
    except Subscription.DoesNotExist:
        logger.warning(
            "Subscription not found: The provided Stripe subscription ID does not exist.",
            extra={"stripe_subscription_id": stripe_subscription_id},
        )


def get_free_subscription(subscription: Subscription):
    return subscription.user.subscriptions.filter(plan__is_free=True).first()
