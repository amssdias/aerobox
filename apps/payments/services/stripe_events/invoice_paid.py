import logging
from datetime import timedelta

from django.utils import timezone

from apps.payments.tasks.send_invoice_paid_email import send_invoice_payment_success_email
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.invoice_event_mixin import StripeInvoiceMixin

logger = logging.getLogger("aerobox")


class InvoicePaidHandler(StripeEventHandler, StripeInvoiceMixin):
    """
    Handles the `invoice.paid` event.
    """

    def process(self):
        invoice_id = self.get_invoice_id()
        payment = self.get_payment(invoice_id)
        payment_method = self.get_payment_method()
        amount = self.extract_amount_paid()
        payment_date = self.extract_payment_date()
        status = self.get_invoice_status()

        if self.can_update(
            invoice_id, payment, payment_method, amount, payment_date, status
        ):
            self.update_payment(payment, payment_method, payment_date, status)
            self.update_subscription(payment.subscription)
            self.send_invoice_paid_email(payment=payment)

    @staticmethod
    def can_update(invoice_id, payment, payment_method, amount, payment_date, status):
        missing_fields = [
            field_name for field_name, value in [
                ("payment", payment),
                ("payment_method", payment_method),
                ("amount", amount),
                ("payment_date", payment_date),
                ("status", status),
            ] if value is None
        ]

        if missing_fields:
            error_msg = (
                f"Invoice ID: {invoice_id} - Payment update failed due to missing fields: {', '.join(missing_fields)}. "
                "Stripe should retry."
            )
            logger.error(error_msg, extra={
                "payment": payment,
                "method": payment_method,
                "amount": amount,
                "date": payment_date,
                "missing_fields": missing_fields,
            })
            raise RuntimeError(error_msg)

        if float(payment.amount) != amount:
            error_msg = (
                f"Invoice ID: {invoice_id} - Payment amount mismatch. Expected: {payment.amount}, Received: {amount}. "
                "Possible double charge or incorrect Stripe data."
            )
            logger.error(error_msg, extra={
                "payment": payment,
                "method": payment_method,
                "expected_amount": payment.amount,
                "received_amount": amount,
                "date": payment_date,
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

        if subscription.end_date and subscription.end_date <= today:
            subscription.end_date = today + timedelta(days=30)
            subscription.save(update_fields=["end_date"])
            logger.info(f"Subscription {subscription.id} extended to {subscription.end_date}.")
        else:
            logger.info(f"Subscription {subscription.id} not updated. Current end date is {subscription.end_date}.")

    @staticmethod
    def send_invoice_paid_email(payment):
        send_invoice_payment_success_email.delay(
            user_id=payment.user.id,
            invoice_pdf_url=payment.invoice_pdf_url
        )
