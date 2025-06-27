import logging
from datetime import datetime, timezone

import stripe

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

    @staticmethod
    def get_stripe_invoice(stripe_invoice_id):
        try:
            return stripe.Invoice.retrieve(stripe_invoice_id, expand=["payments"])

        except stripe.error.InvalidRequestError as e:
            logger.error(
                "Invalid Stripe invoice ID or invoice not found.",
                extra={"stripe_invoice_id": stripe_invoice_id, "error": str(e)}
            )

        except stripe.error.AuthenticationError as e:
            logger.critical(
                "Stripe authentication failed — check your API key.",
                extra={"error": str(e)}
            )

        except stripe.error.APIConnectionError as e:
            logger.error(
                "Network communication with Stripe failed.",
                extra={"error": str(e)}
            )

        except stripe.error.StripeError as e:
            logger.exception(
                "Stripe API error occurred.",
                extra={"error": str(e)}
            )

        except Exception as e:
            logger.exception(
                "Unexpected error while retrieving Stripe invoice.",
                extra={"stripe_invoice_id": stripe_invoice_id, "error": str(e)}
            )

        return None

    @staticmethod
    def get_invoice_subscription_id(invoice: stripe.Invoice):
        return

    @staticmethod
    def convert_cents_to_euros(cents: int) -> float:
        if cents is None:
            logger.error("convert_cents_to_euros received None")
            raise ValueError("Cents value cannot be None")
        if cents < 0:
            logger.error(f"convert_cents_to_euros received negative value: {cents}")
            raise ValueError("Cents value cannot be negative")
        return int(cents) / 100

    @staticmethod
    def get_payment_method(stripe_invoice):
        payment_intent_id = stripe_invoice.payments.get("data")[0].get("payment").get("payment_intent")

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

    @staticmethod
    def get_invoice_paid_date(stripe_invoice):
        paid_timestamp = stripe_invoice.status_transitions.get("paid_at")
        if not paid_timestamp:
            paid_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
            logger.warning(
                f"No 'paid_at' timestamp found in invoice status_transitions. Using current time. Invoice ID: {stripe_invoice.id}"
            )

        return datetime.utcfromtimestamp(paid_timestamp).replace(
            tzinfo=timezone.utc
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
