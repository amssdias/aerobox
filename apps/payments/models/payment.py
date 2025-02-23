from django.db import models
from django.conf import settings

from apps.payments.choices.payment_choices import PaymentStatusChoices, PaymentMethodChoices
from apps.subscriptions.models import Subscription
from config.models import Timestampable


class Payment(Timestampable):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField()
    payment_method = models.CharField(max_length=50, choices=PaymentMethodChoices.choices)
    status = models.CharField(max_length=20, choices=PaymentStatusChoices.choices)

    def __str__(self):
        return f"Payment of ${self.amount} for {self.user.username}"
