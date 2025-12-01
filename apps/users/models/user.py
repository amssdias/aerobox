from django.contrib.auth.models import AbstractUser

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices


class User(AbstractUser):

    @property
    def active_subscription(self):
        return (
            self.subscriptions
            .filter(status=SubscriptionStatusChoices.ACTIVE.value)
            .first()
        )

    @property
    def plan(self):
        sub = self.active_subscription
        return sub.plan if sub else None
