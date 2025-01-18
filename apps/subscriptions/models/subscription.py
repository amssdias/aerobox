from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.subscriptions.models.plan import Plan
from config.models import Timestampable


class Subscription(Timestampable):
    """Tracks a user's subscription, allowing flexible billing cycles."""

    BILLING_CYCLE_CHOICES = [
        ("monthly", _("Monthly")),
        ("yearly", _("Yearly")),
    ]

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("canceled", _("Canceled")),
        ("expired", _("Expired")),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES)
    start_date = models.DateField(default=now)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    is_trial = models.BooleanField(
        default=False,
        help_text=_("Indicates whether this subscription is a free trial.")
    )
    storage_used = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True,
    )

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
        if self.billing_cycle == 'monthly':
            self.end_date = self.start_date + timedelta(days=30)
        elif self.billing_cycle == 'yearly':
            self.end_date = self.start_date + timedelta(days=365)
        self.save()
