from apps.integrations.stripe.payments.billing import get_stripe_invoice
from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.integrations.stripe.payments.mappers.invoice import to_invoice_payment_summary
from apps.integrations.stripe.webhooks.validators import require_event_object, require_object_id


def build_invoice_summary(event: dict) -> InvoicePaymentSummary:
    obj = require_event_object(event)
    invoice_id = require_object_id(obj, what="invoice")
    stripe_invoice_obj = get_stripe_invoice(invoice_id)
    return to_invoice_payment_summary(
        stripe_invoice_obj,
    )
