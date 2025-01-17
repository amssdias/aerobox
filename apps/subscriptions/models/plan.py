from django.db import models
from config.models import Timestampable


class Plan(Timestampable):
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
    storage_limit = models.PositiveIntegerField(help_text="Storage limit in GB")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
