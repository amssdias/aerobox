import logging
from datetime import datetime, timezone

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from apps.payments.services.stripe_api import get_payment_intent, get_payment_method
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler


logger = logging.getLogger("aerobox")


class InvoicePaidHandler(StripeEventHandler):
    """
    Handles the `invoice.paid` event.
    """

    def process(self):
        invoice_id = self.get_invoice_id()
        payment = self.get_payment(invoice_id)
        payment_method = self.get_payment_method()
        amount = self.extract_amount_paid()
        payment_date = self.extract_payment_date()
        status = self.get_status()

        if self.can_update(
            invoice_id, payment, payment_method, amount, payment_date, status
        ):
            self.update_payment(payment, payment_method, amount, payment_date, status)

    def get_invoice_id(self):
        try:
            return self.data["id"]
        except KeyError:
            logger.critical(
                "Missing 'id' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            raise ValueError(
                "Invoice ID is missing in event data. Stripe should retry later."
            )

    @staticmethod
    def get_payment(invoice_id):
        try:
            return Payment.objects.get(stripe_invoice_id=invoice_id)
        except Payment.DoesNotExist:
            logger.error(
                f"Payment record not found for Stripe Invoice ID: {invoice_id}"
            )
            return None

    def get_payment_method(self):
        payment_intent_id = self.data.get("payment_intent")
        if not payment_intent_id:
            logger.error(
                "Missing 'payment_intent' in event data.",
                extra={"stripe_data": self.data},
            )
            return None

        payment_intent = get_payment_intent(payment_intent_id)
        if not payment_intent:
            logger.error(
                f"Failed to retrieve PaymentIntent with ID: {payment_intent_id}"
            )
            return None

        payment_method_id = payment_intent.get("payment_method")
        if not payment_method_id:
            logger.error(
                f"No payment method found in PaymentIntent ID: {payment_intent_id}"
            )
            return None

        payment_method = get_payment_method(payment_method_id)
        if not payment_method:
            logger.error(
                f"Failed to retrieve PaymentMethod with ID: {payment_method_id}"
            )
            return None

        return payment_method["type"]

    def extract_amount_paid(self):
        try:
            return self.data["amount_paid"] / 100  # Convert cents to euros
        except KeyError:
            logger.error(
                "Missing 'amount_paid' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            return None
        except TypeError:
            logger.error(
                "Invalid type for 'amount_paid' in Stripe event data. Expected an integer value in cents, "
                f"but got {type(self.data.get('amount_paid'))} instead.",
                extra={"stripe_data": self.data},
            )
            return None

    def extract_payment_date(self):
        try:
            paid_timestamp = self.data["status_transitions"]["paid_at"]
            return datetime.utcfromtimestamp(paid_timestamp).replace(
                tzinfo=timezone.utc
            )
        except KeyError:
            logger.error(
                "Missing 'status_transitions.paid_at' in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            return None
        except TypeError:
            logger.error(
                "Invalid type for 'status_transitions.paid_at' in Stripe event data. Expected an integer timestamp, "
                f"but got {type(self.data['status_transitions'].get('paid_at'))} instead.",
                extra={"stripe_data": self.data},
            )
            return None

    def get_status(self):
        try:
            if self.data["status"] == "paid":
                return PaymentStatusChoices.PAID.value
        except KeyError:
            logger.error(
                "Missing 'status' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            return None

    @staticmethod
    def can_update(invoice_id, payment, payment_method, amount, payment_date, status):
        if not all([payment, payment_method, payment_date, status]) or amount is None:
            logger.error(
                f"Payment data is incomplete for Invoice ID: {invoice_id}. Stripe should retry.",
                extra={
                    "payment": payment,
                    "method": payment_method,
                    "amount": amount,
                    "date": payment_date,
                },
            )
            raise RuntimeError(
                f"Payment data is incomplete for Invoice ID: {invoice_id}. Stripe should retry."
            )

        return True

    @staticmethod
    def update_payment(payment, payment_method, amount, payment_date, status):
        payment.payment_method = payment_method
        payment.amount = amount
        payment.payment_date = payment_date
        payment.status = status
        payment.save()
