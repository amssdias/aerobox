from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.features.models import Feature
from apps.subscriptions.models import Plan


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text=_("Custom configuration for the feature in this plan"),
    )

    class Meta:
        unique_together = ("plan", "feature")
