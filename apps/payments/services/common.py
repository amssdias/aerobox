import logging

from apps.payments.models import Payment

logger = logging.getLogger("aerobox")


def get_payment(invoice_id):
    try:
        return Payment.objects.get(stripe_invoice_id=invoice_id)
    except Payment.DoesNotExist:
        logger.error(
            f"Payment record not found for Stripe Invoice ID: {invoice_id}"
        )
        return None
