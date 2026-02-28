import logging

from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.payments.constants.stripe_invoice import SUBSCRIPTION_CYCLE
from apps.payments.services.invoices.ensure_payment import get_or_sync_payment_from_stripe
from apps.payments.services.invoices.status_transitions import mark_payment_as_past_due_retrying
from apps.payments.tasks.send_payment_failed_email import send_invoice_payment_failed_email
from apps.subscriptions.services.subscriptions.status_transitions import update_subscription_status_past_due

logger = logging.getLogger("aerobox")


def apply_payment_failed(invoice_payment_summary: InvoicePaymentSummary):
    if not is_subscription_cycle(invoice_payment_summary.billing_reason):
        return

    payment = get_or_sync_payment_from_stripe(invoice_payment_summary)
    if not payment:
        logger.warning(
            "Stripe invoice.payment_failed received but no local Payment found. "
            "Skipping past-due handling. Possible race condition (webhook before Payment creation) "
            "or missing data.",
            extra={
                "stripe_invoice_id": invoice_payment_summary.invoice_id,
                "billing_reason": invoice_payment_summary.billing_reason,
                "event": "invoice.payment_failed",
            },
        )
        return

    mark_payment_as_past_due_retrying(payment)
    update_subscription_status_past_due(payment.subscription)

    logger.info(
        "Payment marked as past_due_retrying after Stripe invoice.payment_failed. "
        "Retries handled by Stripe dunning settings.",
        extra={
            "payment_id": payment.id,
            "user_id": payment.user_id,
            "subscription_id": payment.subscription_id,
            "stripe_invoice_id": invoice_payment_summary.invoice_id,
            "event": "invoice.payment_failed",
        },
    )

    send_invoice_payment_failed_email.delay(
        user_id=payment.user.id,
    )


def is_subscription_cycle(billing_reason):
    return billing_reason == SUBSCRIPTION_CYCLE
