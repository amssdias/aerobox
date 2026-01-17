from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CloudStoragePermanentDeleteAllFilesViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.url = reverse("storage-permanent-delete-all-files")

    def setUp(self):
        self.deleted_file = CloudFileFactory(
            user=self.user,
            file_name="deleted_file.pdf",
            deleted_at=timezone.now()
        )
        self.not_deleted_file = CloudFileFactory(
            user=self.user
        )

        self.client.force_authenticate(user=self.user)

    @patch.object(S3Service, "delete_file")
    def test_user_can_permanently_delete_all_files(self, mock_s3):
        file_name = self.deleted_file.file_name
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CloudFile.objects.filter(file_name=file_name).exists())
        self.assertTrue(CloudFile.objects.filter(file_name=self.not_deleted_file.file_name).exists())
        mock_s3.assert_called()

    @patch.object(S3Service, "delete_file")
    def test_user_cannot_permanently_delete_another_users_file(self, mock_s3):
        user = UserFactory()
        file = CloudFileFactory(user=user, deleted_at=timezone.now())

        response = self.client.delete(self.url)

        self.assertTrue(CloudFile.objects.filter(file_name=file.file_name).exists())
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_permanently_delete_files_if_not_deleted_first(self):
        file = CloudFileFactory(user=self.user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(CloudFile.objects.filter(file_name=file.file_name).exists())

    def test_authenticated_user_required_to_permanently_delete_files(self):
        self.client.logout()
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.cloud_storage.views.cloud_storage.clear_all_deleted_files_from_user.delay")
    def test_delete_files_task_is_called_to_delete_files(self, mock_delete_all_files_from_user):
        self.client.delete(self.url)

        mock_delete_all_files_from_user.assert_called_once()

    @patch.object(S3Service, "delete_file")
    def test_delete_all_files_returns_success_message_and_status(self, mock_s3):
        deleted_files = CloudFile.deleted.all().count()
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsInstance(response.data, dict)
        self.assertEqual(response.data.get("message"), "All files in the recycle bin have been permanently deleted.")
        self.assertEqual(response.data.get("deleted_count"), deleted_files)

    def test_delete_all_files_no_files_to_delete(self):
        self.deleted_file.permanent_delete()

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("message"), "No files found in the recycle bin to delete.")
