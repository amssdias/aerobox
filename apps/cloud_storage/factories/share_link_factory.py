import factory

from apps.cloud_storage.models import ShareLink
from apps.users.factories.user_factory import UserFactory


class ShareLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ShareLink

    owner = factory.SubFactory(UserFactory)

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for file_obj in extracted:
                self.files.add(file_obj)

    @factory.post_generation
    def folders(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for folder_obj in extracted:
                self.folders.add(folder_obj)
