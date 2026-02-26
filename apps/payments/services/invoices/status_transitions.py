from apps.payments.choices.payment_choices import PaymentStatusChoices


def mark_payment_as_past_due_retrying(payment):
    """
    Updates the payment status to "retrying," which corresponds to the "past_due"
    status in Stripe. This indicates that the payment attempt has failed, and
    Stripe will retry the payment based on the configured dunning settings.
    """
    payment.status = PaymentStatusChoices.RETRYING.value
    payment.save()
