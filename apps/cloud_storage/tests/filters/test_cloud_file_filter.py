from django.test import TestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.filters import CloudFileFilter
from apps.cloud_storage.models import CloudFile


class TestCloudFileFilter(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.parent_folder = FolderFactory(name="Parent folder")
        cls.f1 = CloudFileFactory(file_name="A test.pdf", folder=None)
        cls.f2 = CloudFileFactory(file_name="B test.pdf", folder=None)
        cls.f3 = CloudFileFactory(file_name="C test.pdf", folder=cls.parent_folder)

    def test_no_folder_true_returns_only_nulls(self):
        base_qs = CloudFile.not_deleted.all()
        flt = CloudFileFilter(data={"no_folder": True}, queryset=base_qs)
        qs = flt.qs

        self.assertSetEqual(set(qs.values_list("id", flat=True)), {self.f1.id, self.f2.id})

    def test_no_folder_false_returns_only_with_folder(self):
        base_qs = CloudFile.not_deleted.all()
        flt = CloudFileFilter(data={"no_folder": False}, queryset=base_qs)
        qs = flt.qs

        self.assertSetEqual(set(qs.values_list("id", flat=True)), {self.f3.id})

    def test_name_filter_to_file_name(self):
        c = CloudFileFactory(file_name="A note.txt", folder=None)

        base_qs = CloudFile.not_deleted.all()
        flt = CloudFileFilter(data={"name": "A"}, queryset=base_qs)
        qs = flt.qs

        self.assertSetEqual(set(qs.values_list("id", flat=True)), {self.f1.id, c.id})

    def test_name_filter_to_file_name_contains(self):
        base_qs = CloudFile.not_deleted.all()
        flt = CloudFileFilter(data={"name": "test"}, queryset=base_qs)
        qs = flt.qs

        self.assertSetEqual(set(qs.values_list("id", flat=True)), {self.f1.id, self.f2.id, self.f3.id})
