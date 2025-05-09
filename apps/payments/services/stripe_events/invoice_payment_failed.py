import logging

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.constants.stripe_invoice import SUBSCRIPTION_CYCLE
from apps.payments.tasks.send_payment_failed_email import send_invoice_payment_failed_email
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.invoice_event_mixin import (
    StripeInvoiceMixin,
)

logger = logging.getLogger("aerobox")


class InvoicePaymentFailedHandler(StripeEventHandler, StripeInvoiceMixin):
    """
    Handles the `invoice.payment_failed` event.
    """

    def process(self):
        invoice_id = self.get_invoice_id()
        payment = self.get_payment(invoice_id)

        billing_reason = self.get_billing_reason()

        if self.is_subscription_cycle(billing_reason):
            self.update_payment(payment)
            self.send_invoice_payment_failed_email(payment)

    @staticmethod
    def is_subscription_cycle(billing_reason):
        return billing_reason == SUBSCRIPTION_CYCLE

    @staticmethod
    def update_payment(payment):
        """
        Updates the payment status to "retrying," which corresponds to the "past_due"
        status in Stripe. This indicates that the payment attempt has failed, and
        Stripe will retry the payment based on the configured dunning settings.
        """
        payment.status = PaymentStatusChoices.RETRYING.value
        payment.save()
        logger.info(
            f"Payment retrying: Payment ID {payment.id} failed. User ID {payment.user_id} will be retried based on Stripe's dunning settings."
        )

    @staticmethod
    def send_invoice_payment_failed_email(payment):
        send_invoice_payment_failed_email.delay(
            user_id=payment.user.id,
        )
