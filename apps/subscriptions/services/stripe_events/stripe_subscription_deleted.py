import logging
from datetime import datetime

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
)
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.subscription_mixin import StripeSubscriptionMixin

logger = logging.getLogger("aerobox")


class SubscriptionDeleteddHandler(StripeEventHandler, StripeSubscriptionMixin):
    """
    Handles `customer.subscription.deleted` event.
    """

    def process(self):
        subscription_id = self.data["id"]
        subscription = self.get_subscription(stripe_subscription_id=subscription_id)

        if not subscription:
            logger.warning(
                "Received Stripe 'subscription.deleted' event but no matching subscription was found in the database.",
                extra={"stripe_subscription_id": subscription_id}
            )
            return

        stripe_subscription = self.get_stripe_subscription(stripe_subscription_id=subscription_id)
        ended_at = stripe_subscription.ended_at
        self.update_subscription(subscription, ended_at)
        self.reactivate_free_subscription_if_exists(subscription)
        self.cancel_pending_payments(subscription)

    @staticmethod
    def update_subscription(subscription, ended_at):
        subscription.status = SubscriptionStatusChoices.CANCELED.value
        subscription.end_date = (
            datetime.utcfromtimestamp(ended_at).date()
            if ended_at
            else subscription.end_date
        )
        subscription.save(update_fields=["status", "end_date"])

    def reactivate_free_subscription_if_exists(self, subscription):
        free_sub = self.get_free_subscription(subscription)
        if free_sub:
            self.activate_free_subscription(free_sub)

    @staticmethod
    def activate_free_subscription(free_sub):
        if free_sub.status != SubscriptionStatusChoices.ACTIVE.value:
            free_sub.status = SubscriptionStatusChoices.ACTIVE.value
            free_sub.save(update_fields=["status"])

    @staticmethod
    def get_free_subscription(subscription):
        return subscription.user.subscriptions.filter(plan__is_free=True).first()

    @staticmethod
    def cancel_pending_payments(subscription):
        """
        Marks all pending payments related to the subscription as canceled.
        """
        pending_payments = subscription.payments.filter(
            status__in=[
                PaymentStatusChoices.PENDING.value,
                PaymentStatusChoices.RETRYING.value,
            ]
        )

        if pending_payments.exists():
            pending_payments.update(status=PaymentStatusChoices.CANCELED.value)
            logger.info(
                f"Canceled {pending_payments.count()} pending payments for subscription ID: {subscription.id}"
            )
