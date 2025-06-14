import logging
from datetime import timedelta

from django.utils import timezone

from apps.payments.services.stripe_events.invoice_created import InvoiceCreatedHandler
from apps.payments.tasks.send_invoice_paid_email import send_invoice_payment_success_email
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.invoice_event_mixin import StripeInvoiceMixin

logger = logging.getLogger("aerobox")


class InvoicePaidHandler(StripeEventHandler, StripeInvoiceMixin):
    """
    Handles the `invoice.paid` event.
    """

    def process(self):
        stripe_invoice_id = self.get_invoice_id()
        stripe_invoice = self.get_stripe_invoice(stripe_invoice_id=stripe_invoice_id)

        payment_method = self.get_payment_method(stripe_invoice)
        amount = self.convert_cents_to_euros(stripe_invoice.amount_paid)
        payment_date = self.get_invoice_paid_date(stripe_invoice)
        status = self.get_invoice_status(stripe_invoice.status)

        payment = self.get_or_create_payment(stripe_invoice.id)
        if self.can_update(stripe_invoice_id, payment, payment_method, amount, status, ):
            self.update_payment(payment, payment_method, payment_date, status)
            self.update_subscription(payment.subscription)
            self.send_invoice_paid_email(payment=payment)

    def get_or_create_payment(self, stripe_invoice_id):
        payment = self.get_payment(stripe_invoice_id)
        return payment or InvoiceCreatedHandler(event=self.event).handle_payment_creation()

    @staticmethod
    def can_update(invoice_id, payment, payment_method, amount, status):
        missing_fields = [
            field_name for field_name, value in [
                ("payment", payment),
                ("payment_method", payment_method),
                ("status", status),
            ] if not value
        ]

        if amount == "" or amount is None:
            missing_fields.append("amount")

        if missing_fields or float(payment.amount) != amount:
            error_msg = (
                f"Invoice ID: {invoice_id} - Payment update failed due to missing fields: {', '.join(missing_fields)}. "
                "Stripe should retry."
            ) if missing_fields else (
                f"Invoice ID: {invoice_id} - Payment amount mismatch. Expected: {payment.amount}, Received: {amount}. "
                "Possible double charge or incorrect Stripe data."
            )

            logger.error(error_msg, extra={
                "payment": payment,
                "method": payment_method,
                "expected_amount": payment.amount if payment else 0,
                "received_amount": amount,
            })
            raise RuntimeError(error_msg)

        return True

    @staticmethod
    def update_payment(payment, payment_method, payment_date, status):
        payment.payment_method = payment_method
        payment.payment_date = payment_date
        payment.status = status
        payment.save(update_fields=["payment_method", "payment_date", "status"])

    @staticmethod
    def update_subscription(subscription):
        today = timezone.now().date()

        update_fields = []
        if subscription.status != SubscriptionStatusChoices.ACTIVE:
            subscription.status = SubscriptionStatusChoices.ACTIVE.value
            update_fields.append("status")

        if subscription.end_date and subscription.end_date <= today:
            subscription.end_date = today + timedelta(days=30)
            update_fields.append("end_date")
            subscription.save(update_fields=update_fields)
            logger.info(f"Subscription {subscription.id} extended to {subscription.end_date}.")
        else:
            logger.warning(f"Subscription {subscription.id} not updated. Current end date is {subscription.end_date}.")

    @staticmethod
    def send_invoice_paid_email(payment):
        send_invoice_payment_success_email.delay(
            user_id=payment.user.id,
            invoice_pdf_url=payment.invoice_pdf_url
        )
