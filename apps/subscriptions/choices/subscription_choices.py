from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionStatusChoices(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    CANCELED = "canceled", _("Canceled")
    EXPIRED = "expired", _("Expired")
    PAST_DUE = "past_due", _("Past Due")


class SubscriptionBillingCycleChoices(models.TextChoices):
    MONTH = "month", _("Monthly")
    YEAR = "year", _("Yearly")
