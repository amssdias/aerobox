import logging

from apps.payments.choices.payment_choices import PaymentStatusChoices

logger = logging.getLogger("aerobox")


def cancel_pending_payments(payments, subscription_id):
    """
    Marks all pending payments related to a subscription as canceled.
    """
    pending_payments = payments.filter(
        status__in=[
            PaymentStatusChoices.PENDING.value,
            PaymentStatusChoices.RETRYING.value,
        ]
    )

    if pending_payments.exists():
        pending_payments_counter = pending_payments.count()
        pending_payments.update(status=PaymentStatusChoices.CANCELED.value)
        logger.info(
            f"Canceled {pending_payments_counter} pending payments for subscription ID: {subscription_id}"
        )
