from apps.integrations.stripe.subscriptions.dto.subscription import SubscriptionSummary
from apps.integrations.stripe.subscriptions.mappers.subscription import (
    to_subscription_summary,
)
from apps.integrations.stripe.subscriptions.subscription import get_stripe_subscription
from apps.integrations.stripe.webhooks.validators import require_event_object, require_object_id


def build_subscription_summary(event: dict) -> SubscriptionSummary:
    obj = require_event_object(event)
    subscription_id = require_object_id(obj, what="subscription")
    stripe_sub = get_stripe_subscription(subscription_id)
    return to_subscription_summary(stripe_sub)
