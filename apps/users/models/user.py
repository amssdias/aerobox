from django.contrib.auth.models import AbstractUser

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices


class User(AbstractUser):

    @property
    def get_active_subscription(self):
        subscription = self.subscriptions.filter(status=SubscriptionStatusChoices.ACTIVE.value).first()
        return subscription if subscription else None

    @property
    def current_plan(self):
        subscription = self.get_active_subscription()
        plan = subscription.plan
        return plan if plan else None
