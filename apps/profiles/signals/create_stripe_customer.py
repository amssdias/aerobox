from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.integrations.stripe.client import stripe
from apps.profiles.models import Profile


@receiver(post_save, sender=Profile)
def create_stripe_customer(sender, instance, created, **kwargs):
    if created and not instance.stripe_customer_id:
        customer = stripe.Customer.create(
            email=instance.user.email if instance.user.email else None,
            metadata={"user_id": instance.user.id}
        )
        instance.stripe_customer_id = customer.id
        instance.save()
