from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.features.choices.feature_code_choices import FeatureCodeChoices


class Feature(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        choices=FeatureCodeChoices.choices,
        help_text=_("Unique identifier for the feature")
    )
    name = models.JSONField(default=dict)
    description = models.JSONField(default=dict, blank=True, null=True)
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text=_("Optional: store feature-specific config")
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
