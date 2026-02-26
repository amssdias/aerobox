import logging

from django.db import IntegrityError

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.domain.money import cents_to_euros
from apps.payments.models import Payment
from apps.subscriptions.services.subscriptions.ensure_subscription import (
    get_or_sync_subscription_from_stripe,
)

logger = logging.getLogger("aerobox")


def create_invoice(invoice_payment_summary):
    subscription = get_or_sync_subscription_from_stripe(
        stripe_subscription_id=invoice_payment_summary.subscription_id
    )

    user = subscription.user if subscription else None
    amount = cents_to_euros(
        invoice_payment_summary.amount_paid or invoice_payment_summary.amount_due
    )

    if not is_valid_payment(
            user, subscription, invoice_payment_summary.invoice_id, amount
    ):
        return

    return create_payment(
        user=user,
        subscription=subscription,
        status=PaymentStatusChoices.PENDING.value,
        stripe_invoice_id=invoice_payment_summary.invoice_id,
        invoice_url=invoice_payment_summary.hosted_invoice_url,
        invoice_pdf_url=invoice_payment_summary.invoice_pdf,
        amount=amount,
    )


def is_valid_payment(user, subscription, stripe_invoice_id, amount_due):
    missing_fields = []
    if not user:
        missing_fields.append("user")
    if not subscription:
        missing_fields.append("subscription")
    if amount_due is None:
        missing_fields.append("amount_due")

    if missing_fields:
        logger.critical(
            f"Failed to create payment instance for invoice {stripe_invoice_id}. "
            f"Missing required fields: {', '.join(missing_fields)}. "
            "Check if the Stripe event contains valid customer and subscription data.",
            extra={
                "stripe_invoice_id": stripe_invoice_id
            },
        )
        raise RuntimeError(
            f"Payment data is incomplete for Invoice ID: {stripe_invoice_id}. Stripe should retry."
        )

    return True


def create_payment(
        user, subscription, status, stripe_invoice_id, invoice_url, invoice_pdf_url, amount
):
    try:
        payment, created = Payment.objects.get_or_create(
            stripe_invoice_id=stripe_invoice_id,
            defaults={
                "user": user,
                "subscription": subscription,
                "status": status,
                "invoice_url": invoice_url,
                "invoice_pdf_url": invoice_pdf_url,
                "amount": amount,
            },
        )
        logger.info(f"Payment created successfully for invoice {stripe_invoice_id}.")

    except IntegrityError:
        payment = Payment.objects.get(stripe_invoice_id=stripe_invoice_id)

    return payment
