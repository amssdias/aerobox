import logging

from apps.integrations.stripe.client import stripe

logger = logging.getLogger("aerobox")


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


def get_payment_intent(payment_intent_id):
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception as e:
        return None


def get_payment_method(payment_method_id):
    return stripe.PaymentMethod.retrieve(payment_method_id)
