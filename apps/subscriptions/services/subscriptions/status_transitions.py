from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices


def update_cancel_subscription_status(subscription, ended_at):
    subscription.status = SubscriptionStatusChoices.CANCELED.value
    subscription.end_date = ended_at
    subscription.save(update_fields=["status", "end_date"])


def activate_subscription(subscription):
    if subscription.status != SubscriptionStatusChoices.ACTIVE.value:
        subscription.status = SubscriptionStatusChoices.ACTIVE.value
        subscription.save(update_fields=["status"])


def set_subscription_inactive(subscription):
    if subscription.status != SubscriptionStatusChoices.INACTIVE.value:
        subscription.status = SubscriptionStatusChoices.INACTIVE.value
        subscription.save(update_fields=["status"])


def update_subscription_status_past_due(subscription):
    if (
            subscription.status != SubscriptionStatusChoices.PAST_DUE.value
            and subscription.status != SubscriptionStatusChoices.CANCELED.value
    ):
        subscription.status = SubscriptionStatusChoices.PAST_DUE.value
        subscription.save(update_fields=["status"])
