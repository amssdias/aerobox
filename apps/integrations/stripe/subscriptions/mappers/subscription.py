from datetime import datetime

from apps.integrations.stripe.subscriptions.dto.subscription import SubscriptionSummary
from apps.subscriptions.choices.subscription_choices import SubscriptionBillingCycleChoices


def to_subscription_summary(stripe_subscription) -> SubscriptionSummary:
    """
    https://docs.stripe.com/api/subscriptions?api-version=2025-04-30.basil
    """
    return SubscriptionSummary(
        subscription_id=stripe_subscription.get("id"),
        customer_id=stripe_subscription.get("customer"),
        plan_id=stripe_subscription.plan.get("id"),
        billing_cycle_start=get_subscription_billing_cycle_start(stripe_subscription),
        billing_cycle_end=get_subscription_billing_cycle_end(stripe_subscription),
        billing_cycle_interval=get_subscription_billing_cycle_interval(stripe_subscription),
        cancel_at_period_end=stripe_subscription.cancel_at_period_end,
        ended_at=get_subscription_ended_at(stripe_subscription) if stripe_subscription.ended_at else None,
    )


def get_subscription_billing_cycle_start(stripe_subscription):
    return datetime.utcfromtimestamp(
        stripe_subscription.get("items", {}).get("data", [{}])[0].get("current_period_start")
    ).date()


def get_subscription_billing_cycle_end(stripe_subscription):
    return datetime.utcfromtimestamp(
        stripe_subscription.get("items", {}).get("data", [{}])[0].get("current_period_end")
    ).date()


def get_subscription_ended_at(stripe_subscription):
    return datetime.utcfromtimestamp(stripe_subscription.ended_at).date()


def get_billing_cycle_interval_from_subscription_object(stripe_subscription):
    return stripe_subscription.get("items", {}).get("data", [{}])[0].get("plan", {}).get("interval")


def get_subscription_billing_cycle_interval(stripe_subscription):
    interval = get_billing_cycle_interval_from_subscription_object(stripe_subscription)
    if interval in SubscriptionBillingCycleChoices.values:
        return SubscriptionBillingCycleChoices(interval).value
    return None
