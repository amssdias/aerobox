from apps.subscriptions.services.stripe_webhooks.handlers.common import (
    build_subscription_summary,
)
from apps.subscriptions.services.subscriptions.cancel_subscription import (
    cancel_subscription,
)
from apps.subscriptions.services.subscriptions.create_subscription import (
    create_subscription,
)
from apps.subscriptions.services.subscriptions.update_subscription import (
    update_subscription,
)


def handle_subscription_created(event: dict) -> None:
    subscription_summary = build_subscription_summary(event)
    create_subscription(subscription_summary)


def handle_subscription_updated(event: dict) -> None:
    subscription_summary = build_subscription_summary(event)
    update_subscription(subscription_summary)


def handle_subscription_deleted(event: dict) -> None:
    subscription_summary = build_subscription_summary(event)
    cancel_subscription(subscription_summary)
