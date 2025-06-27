import logging

from django.db import transaction, IntegrityError

from apps.profiles.models import Profile
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Plan, Subscription
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.subscription_mixin import StripeSubscriptionMixin

logger = logging.getLogger("aerobox")


class SubscriptionCreateddHandler(StripeEventHandler, StripeSubscriptionMixin):
    """
    Handles `customer.subscription.created` event.
    """

    def process(self):
        self.create_subscription(self.data.get("id"))

    def create_subscription(self, stripe_subscription_id):
        stripe_subscription = self.get_stripe_subscription(stripe_subscription_id=stripe_subscription_id)
        user = self.get_user(stripe_customer_id=stripe_subscription.customer)
        plan = self.get_plan(plan_stripe_price_id=stripe_subscription.plan.get("id"))

        billing_start = self.get_subscription_billing_cycle_start(stripe_subscription)
        billing_end = self.get_subscription_billing_cycle_end(stripe_subscription)
        billing_cycle = self.get_subscription_billing_cycle_interval(stripe_subscription)

        if not user or not plan or not billing_start or not billing_end or not billing_cycle:
            return False

        try:
            with transaction.atomic():
                subscription, created = Subscription.objects.get_or_create(
                    user=user,
                    stripe_subscription_id=stripe_subscription.id,
                    defaults={
                        "plan": plan,
                        "billing_cycle": billing_cycle,
                        "start_date": billing_start,
                        "end_date": billing_end,
                        "status": SubscriptionStatusChoices.INACTIVE.value,
                        "trial_start_date": None,
                        "is_recurring": True,
                    },
                )
        except IntegrityError:
            subscription = Subscription.objects.get(stripe_invoice_id=stripe_subscription.id)

        return subscription

    @staticmethod
    def get_plan(plan_stripe_price_id):
        try:
            return Plan.objects.get(stripe_price_id=plan_stripe_price_id, is_free=False)

        except Plan.DoesNotExist:
            logger.error(
                "No plan found for the given Stripe price ID.", extra={"stripe_price_id": plan_stripe_price_id}
            )

        return None

    @staticmethod
    def get_user(stripe_customer_id):
        """Retrieve the user associated with a Stripe customer ID."""
        try:
            return Profile.objects.get(stripe_customer_id=stripe_customer_id).user
        except Profile.DoesNotExist:
            logger.error("No profile found for the given Stripe customer ID.",
                         extra={"stripe_customer_id": stripe_customer_id})
        return None
