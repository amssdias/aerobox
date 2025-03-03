from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentMethodChoices(models.TextChoices):
    """
    https://docs.stripe.com/api/payment_methods/object
    """
    CARD = "card", _("Credit Card")
    PAYPAL = "paypal", _("PayPal")


class PaymentStatusChoices(models.TextChoices):
    PENDING = "pending", _("Pending")
    PAID = "paid", _("Paid")
    CANCELED = "canceled", _("Canceled (Void)")
    RETRYING = "retrying", _("Retrying")


class PaymentCurrenciesChoices(models.TextChoices):
    EUR = "eur", _("Euro")
