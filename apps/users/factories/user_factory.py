import factory
from django.contrib.auth import get_user_model
from faker import Faker

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
