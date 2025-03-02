import logging

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.customer_event import StripeCustomerMixin

logger = logging.getLogger("aerobox")


class InvoiceCreatedHandler(StripeEventHandler, StripeCustomerMixin):
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

        if not self.is_valid_payment(user, subscription, invoice_id, status):
            return

        self.create_payment(
            user=user,
            subscription=subscription,
            status=status,
            invoice_id=invoice_id,
            invoice_url=hosted_invoice_url,
            invoice_pdf_url=invoice_pdf_url,
        )

    def get_invoice_id(self):
        return self.data.get("id")

    def get_subscription_id(self):
        subscription_id = self.data.get("subscription")
        if not subscription_id:
            logger.error(
                "Missing 'subscription' key in Stripe event data.",
                extra={"stripe_data": self.data}
            )
        return subscription_id

    def get_invoice_status(self):
        data_status = self.data.get("status")
        if not data_status:
            logger.error(
                "Missing 'status' key in Stripe event data.",
                extra={"stripe_data": self.data}
            )
            return PaymentStatusChoices.PENDING.value

        if data_status == "open":
            return PaymentStatusChoices.PENDING.value
        else:
            return None

    def get_hosted_invoice_url(self):
        hosted_invoice_url = self.data.get("hosted_invoice_url")
        if not hosted_invoice_url:
            logger.error(
                "Missing 'hosted_invoice_url' key in Stripe event data.",
                extra={"stripe_data": self.data}
            )
        return hosted_invoice_url

    def get_invoice_pdf_url(self):
        invoice_pdf_url = self.data.get("invoice_pdf")
        if not invoice_pdf_url:
            logger.error(
                "Missing 'invoice_pdf' key in Stripe event data.",
                extra={"stripe_data": self.data}
            )
        return invoice_pdf_url

    def is_valid_payment(self, user, subscription, invoice_id, status):
        missing_fields = []
        if not user:
            missing_fields.append("user")
        if not subscription:
            missing_fields.append("subscription")
        if not invoice_id:
            missing_fields.append("invoice_id")
        if not status:
            missing_fields.append("status")

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
    def create_payment(user, subscription, status, invoice_id, invoice_url, invoice_pdf_url):
        Payment.objects.create(
            user=user,
            subscription=subscription,
            status=status,
            stripe_invoice_id=invoice_id,
            invoice_url=invoice_url,
            invoice_pdf_url=invoice_pdf_url,
        )
        logger.info(f"Payment created successfully for invoice {invoice_id}.")
