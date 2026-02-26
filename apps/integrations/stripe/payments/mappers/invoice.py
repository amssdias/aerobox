import logging
from datetime import datetime, timezone
from typing import Optional

from apps.integrations.stripe.payments.billing import (
    get_payment_intent,
    get_payment_method,
)
from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary

logger = logging.getLogger("aerobox")


def _as_id(value) -> Optional[str]:
    """Stripe may return an ID string or an expanded object dict."""
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("id")
    return None


def _ts_to_dt(ts: Optional[int]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def to_invoice_payment_summary(
        stripe_invoice,
) -> InvoicePaymentSummary:
    """Main mapper for Stripe invoices -> internal DTO."""

    status_transitions = stripe_invoice.get("status_transitions") or {}
    subscription_id = get_subscription_id_from_invoice(stripe_invoice)
    payment_method_type = resolve_invoice_payment_method_type(stripe_invoice)
    end_date = get_subscription_period_end_date(stripe_invoice)

    return InvoicePaymentSummary(
        invoice_id=stripe_invoice.get("id"),
        subscription_id=subscription_id,
        amount_due=stripe_invoice.get("amount_due"),
        amount_paid=stripe_invoice.get("amount_paid"),
        paid_at=_ts_to_dt(status_transitions.get("paid_at")),
        hosted_invoice_url=stripe_invoice.get("hosted_invoice_url"),
        invoice_pdf=stripe_invoice.get("invoice_pdf"),
        billing_reason=stripe_invoice.billing_reason,
        payment_method_type=payment_method_type,
        subscription_period_end_date=end_date,
    )


def get_subscription_id_from_invoice(stripe_invoice):
    return stripe_invoice.parent.get("subscription_details", {}).get("subscription")


def get_subscription_period_end_date(stripe_invoice):
    unix_timestamp = (
        stripe_invoice.lines.get("data", [{}])[0].get("period", {}).get("end")
    )
    return datetime.utcfromtimestamp(unix_timestamp).date()


def resolve_invoice_payment_method_type(stripe_invoice):
    payments_data = stripe_invoice.payments.get("data")
    payment_intent_id = (
        payments_data[0].get("payment", {}).get("payment_intent")
        if payments_data
        else None
    )

    payment_intent = get_payment_intent(payment_intent_id)
    if not payment_intent:
        logger.error(
            f"Failed to retrieve PaymentIntent with ID: {payment_intent_id}. Getting default payment method"
        )
        return None

    payment_method_id = payment_intent.get("payment_method")
    if not payment_method_id:
        logger.error(
            f"No payment method found in PaymentIntent ID: {payment_intent_id}"
        )
        return None

    payment_method = get_payment_method(payment_method_id)
    if not payment_method:
        logger.error(f"Failed to retrieve PaymentMethod with ID: {payment_method_id}")
        return None

    return payment_method["type"]
