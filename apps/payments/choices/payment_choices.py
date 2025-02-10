from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentMethodChoices(models.TextChoices):
    CREDIT_CARD = "credit_card", _("Credit Card")
    DEBIT_CARD = "debit_card", _("Debit Card")
    PAYPAL = "paypal", _("PayPal")


class PaymentStatusChoices(models.TextChoices):
    SUCCESS = "success", _("Success")
    FAILED = "failed", _("Failed")
    PENDING = "pending", _("Pending")
