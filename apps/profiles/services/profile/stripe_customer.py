import logging

from apps.profiles.models import Profile

logger = logging.getLogger("aerobox")


def get_user(stripe_customer_id):
    """Retrieve the user associated with a Stripe customer ID."""
    try:
        return Profile.objects.get(stripe_customer_id=stripe_customer_id).user
    except Profile.DoesNotExist:
        logger.error(
            "No profile found for the given Stripe customer ID.",
            extra={"stripe_customer_id": stripe_customer_id},
        )
    return None
