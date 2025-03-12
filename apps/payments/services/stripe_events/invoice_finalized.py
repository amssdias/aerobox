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
        invoice_id = self.get_invoice_id()
        payment = self.get_payment(invoice_id)
        amount = self.extract_amount_due()

        hosted_invoice_url = self.get_hosted_invoice_url()
        invoice_pdf_url = self.get_invoice_pdf_url()

        if self.can_update(invoice_id, payment, amount, hosted_invoice_url, invoice_pdf_url):
            self.update_payment(payment, amount, hosted_invoice_url, invoice_pdf_url)

    @staticmethod
    def can_update(invoice_id, payment, amount, hosted_invoice_url, invoice_pdf_url):
        missing_fields = [
            field_name for field_name, value in [
                ("payment", payment),
                ("amount", amount),
                ("hosted_invoice_url", hosted_invoice_url),
                ("invoice_pdf_url", invoice_pdf_url),
            ] if value is None
        ]

        if missing_fields:
            error_msg = (
                f"Invoice ID: {invoice_id} - Payment update failed due to missing fields: {', '.join(missing_fields)}. "
                "Stripe should retry."
            )
            logger.error(error_msg, extra={
                "payment": payment,
                "amount": amount,
                "hosted_invoice_url": hosted_invoice_url,
                "invoice_pdf_url": invoice_pdf_url,
                "missing_fields": missing_fields,
            })
            raise RuntimeError(error_msg)

        return True

    @staticmethod
    def update_payment(payment, amount, hosted_invoice_url, invoice_pdf_url):
        payment.amount = amount
        payment.invoice_url = hosted_invoice_url
        payment.invoice_pdf_url = invoice_pdf_url
        payment.save()
