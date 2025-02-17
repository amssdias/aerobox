import stripe
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.profiles.models import Profile

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


@receiver(post_save, sender=Profile)
def create_stripe_customer(sender, instance, created, **kwargs):
    if created and not instance.stripe_customer_id:
        customer = stripe.Customer.create(
            email=instance.user.email if instance.user.email else None,
            metadata={"user_id": instance.user.id}
        )
        instance.stripe_customer_id = customer.id
        instance.save()
