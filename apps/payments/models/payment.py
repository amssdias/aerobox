from django.db import models
from django.conf import settings

from apps.payments.choices.payment_choices import (
    PaymentStatusChoices,
    PaymentMethodChoices,
    PaymentCurrenciesChoices,
)
from apps.subscriptions.models import Subscription
from config.models import Timestampable
from django.utils.translation import gettext_lazy as _



class Payment(Timestampable):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("The date and time when the payment was made."),
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethodChoices.choices, null=True, blank=True,
    )
    status = models.CharField(max_length=20, choices=PaymentStatusChoices.choices)
    currency = models.CharField(
        max_length=3, default=PaymentCurrenciesChoices.EUR.value
    )

    stripe_invoice_id = models.CharField(max_length=60, unique=True)
    invoice_url = models.URLField(blank=True, null=True)
    invoice_pdf_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Payment of ${self.amount} for {self.user.username}"
