from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CloudStorageViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", password="password")

    def setUp(self):
        path = build_s3_path(
            user_id=self.user.id,
            file_name="docs/test.txt",
        )
        self.file = CloudFileFactory(user=self.user, path=path)
        self.url = reverse("storage-detail", kwargs={"pk": self.file.id})
        self.client.force_authenticate(user=self.user)

    def test_soft_delete_file(self):
        response = self.client.delete(self.url)
        self.file.refresh_from_db()

        self.assertIsNotNone(self.file.deleted_at)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_soft_deleted_file_not_in_active_queryset(self):
        self.file.deleted_at = timezone.now()
        self.file.save()
        active_files = CloudFile.not_deleted.all()

        self.assertNotIn(self.file, active_files)

    def test_cannot_delete_nonexistent_file(self):
        invalid_url = reverse("storage-detail", kwargs={"pk": 9999})
        response = self.client.delete(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_file_remains_in_database(self):
        self.client.delete(self.url)
        self.assertTrue(CloudFile.objects.filter(id=self.file.id).exists())
