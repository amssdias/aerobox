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


class CloudStoragePermanentDeleteViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.deleted_file = CloudFileFactory(
            user=self.user,
            file_name="deleted_file.pdf",
            deleted_at=timezone.now()
        )

        self.url = reverse("storage-permanent-delete-file", kwargs={"pk": self.deleted_file.id})
        self.client.force_authenticate(user=self.user)

    @patch.object(S3Service, "delete_file")
    def test_user_can_permanently_delete_own_deleted_file(self, mock_s3):
        file_name = self.deleted_file.file_name
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CloudFile.objects.filter(file_name=file_name).exists())
        mock_s3.assert_called_once()

    def test_user_cannot_permanently_delete_another_users_file(self):
        user = UserFactory()
        file = CloudFileFactory(user=user, deleted_at=timezone.now())
        url = reverse("storage-permanent-delete-file", kwargs={"pk": file.id})

        response = self.client.delete(url)

        self.assertTrue(CloudFile.objects.filter(file_name=file.file_name).exists())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_permanently_delete_file_if_not_deleted_first(self):
        file = CloudFileFactory(user=self.user)
        url = reverse("storage-permanent-delete-file", kwargs={"pk": file.id})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_required_to_permanently_delete_file(self):
        self.client.logout()
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch.object(S3Service, "delete_file")
    def test_s3_service_is_called_to_delete_file_on_s3(self, mock_s3):
        self.client.delete(self.url)

        mock_s3.assert_called_once()

    @patch.object(S3Service, "delete_file")
    def test_permanent_delete_returns_success_message_and_status(self, mock_s3):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsInstance(response.data, dict)
        self.assertEqual(response.data.get("message"), "File permanently deleted.")

    def test_permanent_delete_returns_404_for_nonexistent_file(self):
        url = reverse("storage-permanent-delete-file", kwargs={"pk": 99999})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch.object(S3Service, "delete_file")
    def test_permanent_delete_does_not_affect_other_user_files(self, mock_s3):
        user = UserFactory()
        file = CloudFileFactory(user=user, deleted_at=timezone.now())

        self.client.delete(self.url)

        self.assertTrue(CloudFile.objects.filter(file_name=file.file_name).exists())

    def test_permanent_delete_raise_exception_on_s3(self):
        service = S3Service()
        error_response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "You don’t have permission."
            }
        }
        exception = Exception(error_response, "DeleteObject")

        with patch.object(service.s3_client, "delete_object", side_effect=exception):
            with self.assertRaises(Exception) as ctx:
                self.client.delete(self.url)
