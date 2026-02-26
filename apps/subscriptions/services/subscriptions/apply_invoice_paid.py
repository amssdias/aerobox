import logging

from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.services.common import get_free_subscription
from apps.subscriptions.services.subscriptions.status_transitions import set_subscription_inactive

logger = logging.getLogger("aerobox")


def apply_invoice_paid_to_subscription(subscription, invoice_payment_summary: InvoicePaymentSummary) -> None:
    update_fields = []

    if subscription.status != SubscriptionStatusChoices.ACTIVE.value:
        subscription.status = SubscriptionStatusChoices.ACTIVE.value
        update_fields.append("status")

    new_end_date = invoice_payment_summary.subscription_period_end_date
    if subscription.end_date != new_end_date:
        subscription.end_date = new_end_date
        update_fields.append("end_date")
        logger.info(f"Subscription {subscription.id} extended to {subscription.end_date}.")
    else:
        logger.info(f"Subscription {subscription.id} already up to date (end date: {subscription.end_date}).")

    if update_fields:
        subscription.save(update_fields=update_fields)

    deactivate_existing_free_subscription(subscription)


def deactivate_existing_free_subscription(subscription):
    free_sub = get_free_subscription(subscription)
    if not free_sub:
        logger.warning(f"Subscription free does not exist for user {subscription.user.id}.")
        return
    set_subscription_inactive(free_sub)
