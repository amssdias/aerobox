import logging

from apps.profiles.models import Profile
from apps.subscriptions.models import Subscription

logger = logging.getLogger("aerobox")



class StripeCustomerMixin:
    """
    Base class for 'customer' Stripe events.
    """

    @staticmethod
    def get_user(data):
        """Retrieve the user associated with a Stripe customer ID."""
        try:
            customer_stripe_id = data["customer"]
            return Profile.objects.get(stripe_customer_id=customer_stripe_id).user

        except Profile.DoesNotExist:
            logger.error("No profile found for the given Stripe customer ID.", extra={"stripe_id": customer_stripe_id})
        except KeyError:
            logger.error("Missing 'customer' key in Stripe event data.", extra={"stripe_data": data})
        return None

    @staticmethod
    def get_subscription(subscription_id):
        try:
            return Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            logger.error(
                "Subscription not found: The provided Stripe subscription ID does not exist.",
                extra={"stripe_subscription_id": subscription_id},
            )

    def get_subscription_id(self):
        subscription_id = self.data.get("subscription")
        if not subscription_id:
            logger.error(
                "Missing 'subscription' key in Stripe event data.",
                extra={"stripe_data": self.data}
            )
        return subscription_id
