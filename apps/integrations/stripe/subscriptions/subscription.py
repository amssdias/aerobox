import logging

from apps.integrations.stripe.client import stripe

logger = logging.getLogger("aerobox")


def get_stripe_subscription(stripe_subscription_id):
    try:
        return stripe.Subscription.retrieve(stripe_subscription_id)

    except stripe.error.InvalidRequestError as e:
        logger.error(
            "Invalid Stripe subscription ID or subscription not found.",
            extra={"stripe_subscription_id": stripe_subscription_id, "error": str(e)}
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
            "Unexpected error while retrieving Stripe subscription.",
            extra={"stripe_subscription_id": stripe_subscription_id, "error": str(e)}
        )

    return None
