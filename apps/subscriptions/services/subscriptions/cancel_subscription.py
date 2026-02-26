import logging

from apps.payments.services.invoices.cancel_payments import cancel_pending_payments
from apps.subscriptions.services.common import get_subscription, get_free_subscription
from apps.subscriptions.services.subscriptions.status_transitions import (
    update_cancel_subscription_status,
    activate_subscription,
)
from apps.subscriptions.tasks.send_subscription_cancelled_email import (
    send_subscription_cancelled_email,
)

logger = logging.getLogger("aerobox")


def cancel_subscription(subscription_summary):
    subscription = get_subscription(
        stripe_subscription_id=subscription_summary.subscription_id
    )
    if not subscription:
        logger.warning(
            "Received Stripe 'subscription.deleted' event but no matching subscription was found in the database.",
            extra={"stripe_subscription_id": subscription_summary.subscription_id},
        )
        return

    update_cancel_subscription_status(subscription, subscription_summary.ended_at)
    reactivate_free_subscription(subscription)
    cancel_pending_payments(
        payments=subscription.payments, subscription_id=subscription.id
    )

    send_subscription_cancelled_email.delay(subscription.user.id)
    return subscription


def reactivate_free_subscription(subscription):
    free_sub = get_free_subscription(subscription)
    if free_sub:
        activate_subscription(free_sub)
    else:
        logger.warning(
            "No free subscription found to reactivate for user %s.",
            subscription.user_id,
        )
