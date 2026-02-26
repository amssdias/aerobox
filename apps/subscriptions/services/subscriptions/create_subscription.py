from django.db import IntegrityError

from apps.integrations.stripe.subscriptions.dto.subscription import SubscriptionSummary
from apps.profiles.services.profile.stripe_customer import get_user
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.plans.get_plan import get_plan


def create_subscription(stripe_subscription: SubscriptionSummary):
    user = get_user(stripe_subscription.customer_id)
    plan = get_plan(plan_stripe_price_id=stripe_subscription.plan_id)

    if (
            not user or
            not plan or
            not stripe_subscription.billing_cycle_start or
            not stripe_subscription.billing_cycle_end or
            not stripe_subscription.billing_cycle_interval
    ):
        return False

    try:
        subscription, created = Subscription.objects.get_or_create(
            stripe_subscription_id=stripe_subscription.subscription_id,
            defaults={
                "plan": plan,
                "user": user,
                "billing_cycle": stripe_subscription.billing_cycle_interval,
                "start_date": stripe_subscription.billing_cycle_start,
                "end_date": stripe_subscription.billing_cycle_end,
                "status": SubscriptionStatusChoices.INACTIVE.value,
                "trial_start_date": None,
                "is_recurring": True,
            },
        )
    except IntegrityError:
        subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription.subscription_id)

    return subscription
