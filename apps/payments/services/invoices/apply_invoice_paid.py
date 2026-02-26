import logging
from decimal import Decimal

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.domain.money import cents_to_euros
from apps.payments.services.invoices.ensure_payment import get_or_sync_payment_from_stripe
from apps.payments.tasks.send_invoice_paid_email import (
    send_invoice_payment_success_email,
)
from apps.subscriptions.services.subscriptions.apply_invoice_paid import (
    apply_invoice_paid_to_subscription,
)

logger = logging.getLogger("aerobox")


def apply_invoice_paid(invoice_payment_summary):
    payment = get_or_sync_payment_from_stripe(
        invoice_payment_summary
    )

    amount_paid_cents = cents_to_euros(invoice_payment_summary.amount_paid)

    if can_update(
            payment,
            invoice_payment_summary.invoice_id,
            invoice_payment_summary.payment_method_type,
            amount_paid_cents,
    ):
        update_payment(payment, invoice_payment_summary, amount_paid_cents)
        apply_invoice_paid_to_subscription(
            payment.subscription, invoice_payment_summary
        )
        send_invoice_paid_email(payment=payment)


def can_update(payment, invoice_id, payment_method, amount):
    missing_fields = [
        field_name
        for field_name, value in [
            ("payment", payment),
            ("payment_method", payment_method),
        ]
        if not value
    ]

    if amount == "" or amount is None:
        missing_fields.append("amount")

    if missing_fields or Decimal(payment.amount) != amount:
        error_msg = (
            (
                f"Invoice ID: {invoice_id} - Payment update failed due to missing fields: {', '.join(missing_fields)}. "
                "Stripe should retry."
            )
            if missing_fields
            else (
                f"Invoice ID: {invoice_id} - Payment amount mismatch. Expected: {payment.amount}, Received: {amount}. "
                "Possible double charge or incorrect Stripe data."
            )
        )

        logger.error(
            error_msg,
            extra={
                "payment": payment,
                "method": payment_method,
                "expected_amount": payment.amount if payment else 0,
                "received_amount": amount,
            },
        )
        raise ValueError(error_msg)

    return True


def update_payment(payment, invoice_payment_summary, amount_paid_cents):
    payment.payment_method = invoice_payment_summary.payment_method_type
    payment.payment_date = invoice_payment_summary.paid_at
    payment.status = PaymentStatusChoices.PAID.value
    update_fields = ["payment_method", "payment_date", "status"]

    hosted_invoice_url = invoice_payment_summary.hosted_invoice_url
    invoice_pdf_url = invoice_payment_summary.invoice_pdf

    # Change to cents
    if payment.amount != amount_paid_cents:
        payment.amount = amount_paid_cents
        update_fields.append("amount")

    if payment.invoice_url != hosted_invoice_url:
        payment.invoice_url = hosted_invoice_url
        update_fields.append("invoice_url")

    if payment.invoice_pdf_url != invoice_pdf_url:
        payment.invoice_pdf_url = invoice_pdf_url
        update_fields.append("invoice_pdf_url")

    payment.save(update_fields=update_fields)


def send_invoice_paid_email(payment):
    send_invoice_payment_success_email.delay(
        user_id=payment.user.id, invoice_pdf_url=payment.invoice_pdf_url
    )
