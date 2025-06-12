import logging
from datetime import datetime

import stripe

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices, SubscriptionBillingCycleChoices
from apps.subscriptions.constants.stripe_subscription_status import INCOMPLETE, PAST_DUE, ACTIVE
from apps.subscriptions.models import Subscription

logger = logging.getLogger("aerobox")


class StripeSubscriptionMixin:
    """
    Base class for 'subscription' Stripe events.
    """

    @staticmethod
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

    @staticmethod
    def get_subscription(stripe_subscription_id):
        try:
            return Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
        except Subscription.DoesNotExist:
            logger.warning(
                "Subscription not found: The provided Stripe subscription ID does not exist.",
                extra={"stripe_subscription_id": stripe_subscription_id},
            )

    @staticmethod
    def get_subscription_status(status):
        if not status:
            return None

        # PAST_DUE: When a user's payment fails, the subscription is marked as inactive.
        if status in [INCOMPLETE, PAST_DUE]:
            return SubscriptionStatusChoices.INACTIVE.value
        elif status == ACTIVE:
            return SubscriptionStatusChoices.ACTIVE.value

    @staticmethod
    def get_subscription_billing_cycle_start(stripe_subscription):
        return datetime.utcfromtimestamp(
            stripe_subscription.get("items", {}).get("data", [{}])[0].get("current_period_start")
        ).date()

    @staticmethod
    def get_subscription_billing_cycle_end(stripe_subscription):
        return datetime.utcfromtimestamp(
            stripe_subscription.get("items", {}).get("data", [{}])[0].get("current_period_end")
        ).date()

    @staticmethod
    def get_billing_cycle_interval_from_subscription_object(stripe_subscription):
        return stripe_subscription.get("items", {}).get("data", [{}])[0].get("plan", {}).get("interval")

    def get_subscription_billing_cycle_interval(self, stripe_subscription):
        interval = self.get_billing_cycle_interval_from_subscription_object(stripe_subscription)
        if interval in SubscriptionBillingCycleChoices.values:
            return SubscriptionBillingCycleChoices(interval).value
        return None
