from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentMethodChoices(models.TextChoices):
    """
    https://docs.stripe.com/api/payment_methods/object
    """
    CARD = "card", _("Credit Card")
    PAYPAL = "paypal", _("PayPal")


class PaymentStatusChoices(models.TextChoices):
    SUCCESS = "success", _("Success")
    FAILED = "failed", _("Failed")
    PENDING = "pending", _("Pending")
