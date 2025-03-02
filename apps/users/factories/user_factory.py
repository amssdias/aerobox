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
    def _create(cls, model_class, *args, disable_signals=True, **kwargs):
        if disable_signals:
            post_save.disconnect(create_stripe_customer, sender=Profile)

        user = super()._create(model_class, *args, **kwargs)
        user.profile.stripe_customer_id = "cus_test"
        user.profile.save()

        if disable_signals:
            post_save.connect(create_stripe_customer, sender=Profile)

        return user