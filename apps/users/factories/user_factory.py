import factory
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from faker import Faker

from apps.profiles.models import Profile
from apps.profiles.signals import create_stripe_customer

User = get_user_model()
fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyAttribute(lambda _: fake.user_name())
    email = factory.LazyAttribute(lambda _: fake.email())
    password = factory.PostGenerationMethodCall("set_password", "StrongPassword123!")

    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())

    @classmethod
    def create(cls, **kwargs):
        """Temporarily disable only the Stripe signal"""
        post_save.disconnect(create_stripe_customer, sender=Profile)

        user = super().create(**kwargs)

        post_save.connect(create_stripe_customer, sender=Profile)
        return user
