import logging
from typing import Tuple

from django.db import models

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.models import Feature
from config.models import Timestampable

logger = logging.getLogger("aerobox")


class Plan(Timestampable):
    features = models.ManyToManyField(
        Feature, through="PlanFeature", related_name="plans"
    )
    name = models.JSONField(default=dict)
    description = models.JSONField(default=dict)
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
    is_free = models.BooleanField(default=False)

    def __str__(self):
        return self.name.get("en", "Unamed plan")

    @property
    def max_storage_bytes(self):
        val = self._compute_storage_limit_bytes()
        return val

    def _compute_storage_limit_bytes(self):
        meta = self.effective_feature_metadata(FeatureCodeChoices.CLOUD_STORAGE.value)
        max_storage_mb = meta.get("max_storage_mb")
        if max_storage_mb is None:
            return None

        BYTES_IN_MB = 1024 * 1024
        try:
            max_storage_mb = int(max_storage_mb)
            if max_storage_mb < 0:
                logger.error(
                    f"Invalid max_storage_mb value ({max_storage_mb}) detected for plan ID '{self.id}'.",
                    extra={
                        "plan_id": self.id,
                        "invalid_max_storage_mb": max_storage_mb,
                    }
                )
                return None
            return max_storage_mb * BYTES_IN_MB
        except (TypeError, ValueError):
            return None

    def effective_feature_metadata(self, feature_code: str) -> dict:
        """
        Merge default Feature.metadata with PlanFeatures.metadata (override wins).
        Returns {} if neither exists.
        """
        main_feature, default_feature = self._get_main_and_default_feature_metadata(feature_code)
        base = (getattr(default_feature, "metadata", None) or {}).copy()
        override = getattr(main_feature, "metadata", None) or {}
        base.update(override)
        return base

    def _get_main_and_default_feature_metadata(self, feature_code) -> Tuple:
        """
        Returns (main_feature, default_feature) for a given feature code.
        main_feature is the PlanFeatures row if present, else None.
        default_feature is the Feature row (may be None if not found).
        """
        main_feature = getattr(self, "plan_features", None) and \
                       self.plan_features.filter(
                           feature__code=feature_code
                       ).first()

        default_feature = None
        if not main_feature:
            default_feature = getattr(self, "features", None) and \
                              self.features.filter(code=feature_code).first()
        else:
            default_feature = main_feature.feature

        return main_feature, default_feature
