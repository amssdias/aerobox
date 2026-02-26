from apps.integrations.stripe.payments.billing import get_stripe_invoice
from apps.integrations.stripe.payments.mappers.invoice import to_invoice_payment_summary
from apps.payments.services.common import get_payment
from apps.payments.services.invoices.create_invoice import create_invoice


def get_or_sync_payment_from_stripe(invoice_payment_summary):
    payment = get_payment(invoice_payment_summary.invoice_id)
    return (
        payment
        if payment
        else create_payment_from_stripe(invoice_payment_summary.invoice_id)
    )


def create_payment_from_stripe(stripe_invoice_id):
    stripe_invoice = get_stripe_invoice(stripe_invoice_id)
    subscription_summary = to_invoice_payment_summary(stripe_invoice)
    return create_invoice(subscription_summary)
