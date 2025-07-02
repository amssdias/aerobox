import logging

from apps.payments.choices.payment_choices import PaymentStatusChoices
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

        payment = self.get_or_create_payment(stripe_invoice.id)
        if self.can_update(stripe_invoice_id, payment, payment_method, amount):
            self.update_payment(payment, payment_method, payment_date)
            self.update_subscription(payment.subscription, stripe_invoice)
            self.send_invoice_paid_email(payment=payment)

    def get_or_create_payment(self, stripe_invoice_id):
        payment = self.get_payment(stripe_invoice_id)
        return payment or InvoiceCreatedHandler(event=self.event).handle_payment_creation()

    @staticmethod
    def can_update(invoice_id, payment, payment_method, amount):
        missing_fields = [
            field_name for field_name, value in [
                ("payment", payment),
                ("payment_method", payment_method),
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
    def update_payment(payment, payment_method, payment_date):
        payment.payment_method = payment_method
        payment.payment_date = payment_date
        payment.status = PaymentStatusChoices.PAID.value
        payment.save(update_fields=["payment_method", "payment_date", "status"])

    def update_subscription(self, subscription, stripe_invoice):
        update_fields = []

        if subscription.status != SubscriptionStatusChoices.ACTIVE.value:
            subscription.status = SubscriptionStatusChoices.ACTIVE.value
            update_fields.append("status")

        new_end_date = self.get_subscription_period_end_date(stripe_invoice)
        if subscription.end_date != new_end_date:
            subscription.end_date = new_end_date
            update_fields.append("end_date")
            logger.info(f"Subscription {subscription.id} extended to {subscription.end_date}.")
        else:
            logger.info(f"Subscription {subscription.id} already up to date (end date: {subscription.end_date}).")

        if update_fields:
            subscription.save(update_fields=update_fields)

        self.deactivate_existing_free_subscription(subscription)

    @staticmethod
    def deactivate_existing_free_subscription(subscription):
        free_sub = subscription.user.subscriptions.filter(plan__is_free=True).first()
        if free_sub and free_sub.status != SubscriptionStatusChoices.INACTIVE.value:
            free_sub.status = SubscriptionStatusChoices.INACTIVE.value
            free_sub.save(update_fields=["status"])

    @staticmethod
    def send_invoice_paid_email(payment):
        send_invoice_payment_success_email.delay(
            user_id=payment.user.id,
            invoice_pdf_url=payment.invoice_pdf_url
        )
