import factory

from apps.cloud_storage.models import Folder
from apps.users.factories.user_factory import UserFactory


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folder

    name = factory.Sequence(lambda n: f"Folder {n}")
    user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def parent(self, create, extracted, **kwargs):
        """
        Allows creating a folder with or without a parent folder.
        Example: FolderFactory(parent=some_folder)
        """
        if extracted:
            self.parent = extracted
            if create:
                self.save()
