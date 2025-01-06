import factory
import random
import string

from apps.cloud_storage.models import CloudFile
from apps.users.factories.user_factory import UserFactory


class CloudFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CloudFile

    file_name = factory.LazyAttribute(lambda _: ''.join(random.choices(string.ascii_letters, k=10)) + ".txt")
    path = factory.LazyAttribute(lambda obj: f"users/user-id/{obj.file_name}")
    size = factory.LazyAttribute(lambda _: random.randint(1000, 1000000))
    content_type = "application/octet-stream"
    user = factory.SubFactory(UserFactory)
