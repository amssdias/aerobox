from apps.subscriptions.services.common import get_subscription
from apps.subscriptions.services.subscriptions.status_transitions import update_cancel_subscription_status


def update_subscription(subscription_summary):
    # plan_id = previous_attributes and previous_attributes.get("plan", {}).get("id")
    # # Change from one subscription to another one
    # if plan_id and subscription and subscription.plan.stripe_price_id == plan_id:
    #     self.change_plan_subscription(subscription, stripe_subscription)

    if subscription_summary.cancel_at_period_end:
        subscription = get_subscription(subscription_summary.subcription_id)
        if subscription:
            update_cancel_subscription_status(subscription, subscription_summary.ended_at)

    return True
