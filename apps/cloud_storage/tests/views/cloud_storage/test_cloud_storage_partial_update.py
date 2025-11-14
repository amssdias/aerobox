from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED, PENDING
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.models import CloudFile
from apps.users.factories.user_factory import UserFactory


class CloudFilePartialUpdateIntegrationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.cloud_file = CloudFileFactory(
            file_name="new_name.txt",
            status=PENDING,
            size=500,
            content_type="aaa/ttt",
            metadata={},
            user=cls.user
        )
        cls.url = reverse("storage-detail", args=[cls.cloud_file.pk])

    def setUp(self):
        self.client.force_authenticate(self.user)

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_partial_update_syncs_when_success(self, mock_s3_head):
        mock_s3_head.return_value = {
            "size": 12345,
            "content_type": "text/plain",
            "metadata": {"foo": "bar"},
        }

        response = self.client.patch(self.url, {"status": SUCCESS}, format="json")

        self.assertEqual(response.status_code, 200)
        mock_s3_head.assert_called_once_with(self.cloud_file.s3_key)

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_partial_update_does_not_sync_when_status_is_not_success(self, mock_s3_head):
        payload = {
            "status": "failed",
            "error_message": "Some error happened",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        mock_s3_head.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.file_name, "new_name.txt")
        self.assertEqual(cf.size, 500)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, FAILED)

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_partial_update_does_not_sync_when_file_is_not_found(self, mock_s3_head):
        mock_s3_head.return_value = None
        payload = {
            "status": SUCCESS,
            "error_message": "",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, 422)

        mock_s3_head.assert_called_once()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.file_name, "new_name.txt")
        self.assertEqual(cf.size, 500)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, FAILED)
        self.assertEqual(cf.error_message,
                         "File upload verification failed: the file could not be found in storage. Please try uploading again.")
