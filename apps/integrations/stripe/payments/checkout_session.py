import logging

from apps.integrations.stripe.client import stripe
from apps.integrations.stripe.payments.exceptions import StripeCheckoutSessionNotFoundError, StripeCheckoutSessionError

logger = logging.getLogger("aerobox")


def get_stripe_session(session_id: str):
    """https://docs.stripe.com/api/checkout/sessions/object?api-version=2025-04-30.basil&lang=python"""
    try:
        return stripe.checkout.Session.retrieve(
            session_id,
            expand=[
                "customer",
            ],
        )

    except stripe.error.InvalidRequestError as e:
        logger.warning(
            "Stripe checkout session not found or invalid request.",
            extra={"session_id": session_id, "error": str(e)}
        )
        raise StripeCheckoutSessionNotFoundError(
            "Checkout session not found."
        ) from e

    except stripe.error.AuthenticationError as e:
        logger.critical(
            "Stripe authentication failed — check your API key.",
            extra={"error": str(e)}
        )
        raise StripeCheckoutSessionError(
            "Unable to authenticate with Stripe."
        ) from e

    except stripe.error.APIConnectionError as e:
        logger.error(
            "Network communication with Stripe failed.",
            extra={"error": str(e)}
        )
        raise StripeCheckoutSessionError(
            "Unable to communicate with Stripe."
        ) from e

    except stripe.error.StripeError as e:
        logger.exception(
            "Stripe API error occurred.",
            extra={"session_id": session_id, "error": str(e)}
        )
        raise StripeCheckoutSessionError(
            "Stripe error while retrieving checkout session."
        ) from e

    except Exception as e:
        logger.exception(
            "Unexpected error while retrieving Stripe session.",
            extra={"session_id": session_id, "error": str(e)}
        )
        raise StripeCheckoutSessionError(
            "Unexpected error while retrieving checkout session."
        ) from e
