from django.db import models

from apps.features.models import Feature
from config.models import Timestampable


class Plan(Timestampable):
    features = models.ManyToManyField(
        Feature, through="PlanFeature", related_name="plans"
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    yearly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    trial_duration_days = models.PositiveIntegerField(
        default=14,
        help_text="Duration of the free trial period in days",
        null=True,
        blank=True,
    )
    stripe_price_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
