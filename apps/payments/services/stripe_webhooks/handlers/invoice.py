import logging

from apps.payments.services.invoices.apply_invoice_paid import apply_invoice_paid
from apps.payments.services.invoices.create_invoice import create_invoice
from apps.payments.services.invoices.failed_payment import apply_payment_failed
from apps.payments.services.stripe_webhooks.handlers.common import build_invoice_summary

logger = logging.getLogger(__name__)


def handle_invoice_created(event: dict) -> None:
    """Handles Stripe `invoice.created`."""
    invoice_payment_summary = build_invoice_summary(event)
    create_invoice(invoice_payment_summary)


def handle_invoice_paid(event: dict) -> None:
    """Handles Stripe `invoice.paid`."""
    invoice_payment_summary = build_invoice_summary(event)
    apply_invoice_paid(invoice_payment_summary)


def handle_invoice_payment_failed(event: dict) -> None:
    """Handles Stripe `invoice.payment_failed`."""
    invoice_payment_summary = build_invoice_summary(event)
    apply_payment_failed(invoice_payment_summary)
