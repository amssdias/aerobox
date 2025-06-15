import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.subscriptions.choices.subscription_choices import SubscriptionBillingCycleChoices, SubscriptionStatusChoices
from apps.subscriptions.models import Plan, Subscription

logger = logging.getLogger("aerobox")
User = get_user_model()

@receiver(post_save, sender=User)
def create_basic_subscription(sender, instance, created, *args, **kwargs):
    if created:
        plan = Plan.objects.filter(is_free=True, is_active=True).first()
        if not plan:
            logger.critical("App must have a free plan active for the user!")
            return

        Subscription.objects.create(
            user=instance,
            plan=plan,
            billing_cycle=SubscriptionBillingCycleChoices.MONTH,
            status=SubscriptionStatusChoices.ACTIVE
        )
