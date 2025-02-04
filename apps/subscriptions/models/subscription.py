from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionStatusChoices,
    SubscriptionBillingCycleChoices,
)
from apps.subscriptions.models.plan import Plan
from config.models import Timestampable


class Subscription(Timestampable):
    """
    Tracks a user's subscription, allowing flexible billing cycles.

    - Each user can have only one active subscription at a time.
    - `is_recurring` determines whether the subscription auto-renews.
    - `end_date` indicates when the subscription expires or needs renewal.
    - If payment fails:
        - `is_recurring` is set to False.
        - The subscription remains valid until `end_date` but will not renew.

    - The first subscription to a plan may have a free trial if the plan allows it.
    - The `trial_start_date` field tracks whether a user has taken a trial before.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    billing_cycle = models.CharField(
        max_length=10, choices=SubscriptionBillingCycleChoices.choices
    )
    start_date = models.DateField(default=now)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=SubscriptionStatusChoices.choices,
        default=SubscriptionStatusChoices.ACTIVE.value,
    )
    trial_start_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("Date when the trial started, if applicable."),
    )
    is_recurring = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def upgrade(self, new_plan):
        """Handles plan upgrades by deactivating current subscription and creating a new one"""
        return

    def cancel(self):
        """Cancels the subscription"""
        return

    def set_end_date(self):
        """Automatically sets end date based on the user's selected billing cycle."""
        if self.billing_cycle == "monthly":
            self.end_date = self.start_date + timedelta(days=30)
        elif self.billing_cycle == "yearly":
            self.end_date = self.start_date + timedelta(days=365)
        self.save()
