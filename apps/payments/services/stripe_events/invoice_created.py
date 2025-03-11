import logging

from apps.payments.models import Payment
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.customer_event import StripeCustomerMixin
from config.services.stripe_services.stripe_events.invoice_event_mixin import StripeInvoiceMixin

logger = logging.getLogger("aerobox")


class InvoiceCreatedHandler(
    StripeEventHandler,
    StripeCustomerMixin,
    StripeInvoiceMixin
):
    """
    Handles the `invoice.created` event.
    """

    def process(self):
        invoice_id = self.get_invoice_id()
        user = self.get_user(data=self.data)
        subscription = self.get_subscription(subscription_id=self.get_subscription_id())
        status = self.get_invoice_status()
        hosted_invoice_url = self.get_hosted_invoice_url()
        invoice_pdf_url = self.get_invoice_pdf_url()
        amount_due = self.extract_amount_due()

        if not self.is_valid_payment(user, subscription, invoice_id, status, amount_due):
            return

        self.create_payment(
            user=user,
            subscription=subscription,
            status=status,
            invoice_id=invoice_id,
            invoice_url=hosted_invoice_url,
            invoice_pdf_url=invoice_pdf_url,
            amount_due=amount_due,
        )

    def is_valid_payment(self, user, subscription, invoice_id, status, amount_due):
        missing_fields = []
        if not user:
            missing_fields.append("user")
        if not subscription:
            missing_fields.append("subscription")
        if not invoice_id:
            missing_fields.append("invoice_id")
        if not status:
            missing_fields.append("status")
        if not amount_due:
            missing_fields.append("amount_due")

        if missing_fields:
            logger.critical(
                f"Failed to create payment instance for invoice {invoice_id}. "
                f"Missing required fields: {', '.join(missing_fields)}. "
                "Check if the Stripe event contains valid customer and subscription data.",
                extra={"stripe_data": self.data},
            )
            raise RuntimeError(f"Payment data is incomplete for Invoice ID: {invoice_id}. Stripe should retry.")

        return True

    @staticmethod
    def create_payment(user, subscription, status, invoice_id, invoice_url, invoice_pdf_url, amount_due):
        Payment.objects.create(
            user=user,
            subscription=subscription,
            status=status,
            stripe_invoice_id=invoice_id,
            invoice_url=invoice_url,
            invoice_pdf_url=invoice_pdf_url,
            amount=amount_due
        )
        logger.info(f"Payment created successfully for invoice {invoice_id}.")
