import logging

from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.invoice_event_mixin import StripeInvoiceMixin

logger = logging.getLogger("aerobox")


class InvoiceFinalizedHandler(StripeEventHandler, StripeInvoiceMixin):
    """
    Handles the `invoice.finalized` event.

    This event is triggered when an invoice is finalized, typically for auto-renewals.
    The handler updates the associated payment record with the latest invoice details,
    including the invoice amount and URLs.
    """

    def process(self):
        stripe_invoice_id = self.get_invoice_id()
        stripe_invoice = self.get_stripe_invoice(stripe_invoice_id=stripe_invoice_id)

        amount_due = self.convert_cents_to_euros(stripe_invoice.amount_due)
        hosted_invoice_url = stripe_invoice.hosted_invoice_url
        invoice_pdf_url = stripe_invoice.invoice_pdf

        if not self.validate_fields(stripe_invoice.id, amount_due, hosted_invoice_url, invoice_pdf_url):
            logger.warning(f"Skipping payment update for invoice {stripe_invoice.id} due to missing data.")
            return

        payment = self.get_payment(stripe_invoice.id)
        self.update_payment(payment, amount_due, hosted_invoice_url, invoice_pdf_url)

    def get_payment(self, stripe_invoice_id):
        payment = super().get_payment(stripe_invoice_id)
        if payment is None:
            raise RuntimeError(f"No Payment found for invoice ID: {stripe_invoice_id}")
        return payment


    @staticmethod
    def validate_fields(invoice_id, amount, hosted_invoice_url, invoice_pdf_url):
        missing_fields = [
            name for name, value in [
                ("amount", amount),
                ("hosted_invoice_url", hosted_invoice_url),
                ("invoice_pdf_url", invoice_pdf_url),
            ] if value is None
        ]

        if missing_fields:
            logger.error(
                f"Invoice ID: {invoice_id} - Missing fields during finalize: {', '.join(missing_fields)}",
                extra={
                    "invoice_id": invoice_id,
                    "amount": amount,
                    "hosted_invoice_url": hosted_invoice_url,
                    "invoice_pdf_url": invoice_pdf_url,
                    "missing_fields": missing_fields,
                }
            )
            return False

        return True

    @staticmethod
    def update_payment(payment, amount, hosted_invoice_url, invoice_pdf_url):
        payment.amount = amount
        payment.invoice_url = hosted_invoice_url
        payment.invoice_pdf_url = invoice_pdf_url
        payment.save()
