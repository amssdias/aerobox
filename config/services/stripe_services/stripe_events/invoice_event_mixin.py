import logging
from datetime import datetime, timezone

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.constants.stripe_invoice import OPEN, DRAFT, PAID
from apps.payments.models import Payment
from apps.payments.services.stripe_api import get_payment_intent, get_payment_method

logger = logging.getLogger("aerobox")


class StripeInvoiceMixin:
    """
    Base class for 'customer' Stripe events.
    """

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

    def get_invoice_status(self):
        data_status = self.data.get("status")
        if not data_status:
            logger.error(
                "Missing 'status' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            return None

        if data_status in [OPEN, DRAFT]:
            return PaymentStatusChoices.PENDING.value
        elif data_status == PAID:
            return PaymentStatusChoices.PAID.value
        else:
            return None

    def get_hosted_invoice_url(self):
        hosted_invoice_url = self.data.get("hosted_invoice_url")
        if not hosted_invoice_url:
            logger.error(
                "Missing 'hosted_invoice_url' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
        return hosted_invoice_url

    def get_invoice_pdf_url(self):
        invoice_pdf_url = self.data.get("invoice_pdf")
        if not invoice_pdf_url:
            logger.error(
                "Missing 'invoice_pdf' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
        return invoice_pdf_url

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

    def extract_amount_due(self):
        try:
            return self.data["amount_due"] / 100  # Convert cents to euros
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

    def get_billing_reason(self):
        try:
            return self.data["billing_reason"]
        except KeyError:
            logger.error(
                "Missing 'billing_reason' key in Stripe event data.",
                extra={"stripe_data": self.data},
            )
            return None

    @staticmethod
    def get_payment(invoice_id):
        try:
            return Payment.objects.get(stripe_invoice_id=invoice_id)
        except Payment.DoesNotExist:
            logger.error(
                f"Payment record not found for Stripe Invoice ID: {invoice_id}"
            )
            return None
