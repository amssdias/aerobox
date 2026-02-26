import logging

from apps.payments.constants.stripe_invoice import SUBSCRIPTION_CYCLE
from apps.payments.services.common import get_payment
from apps.payments.services.invoices.status_transitions import mark_payment_as_past_due_retrying
from apps.payments.tasks.send_payment_failed_email import send_invoice_payment_failed_email
from apps.subscriptions.services.subscriptions.status_transitions import update_subscription_status_past_due

logger = logging.getLogger("aerobox")


def apply_payment_failed(invoice_payment_summary):
    if is_subscription_cycle(invoice_payment_summary.billing_reason):
        payment = get_payment(invoice_payment_summary.invoice_id)
        mark_payment_as_past_due_retrying(payment)
        update_subscription_status_past_due(payment.subscription)
        logger.info(
            f"Payment retrying: Payment ID {payment.id} failed. User ID {payment.user_id} will be retried based on Stripe's dunning settings."
        )

        send_invoice_payment_failed_email.delay(
            user_id=payment.user.id,
        )


def is_subscription_cycle(billing_reason):
    return billing_reason == SUBSCRIPTION_CYCLE
