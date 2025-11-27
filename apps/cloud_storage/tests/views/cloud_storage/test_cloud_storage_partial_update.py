from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.choices.cloud_file_error_code_choices import CloudFileErrorCode
from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED, PENDING
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.models import CloudFile
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class CloudFilePartialUpdateIntegrationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
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

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_syncs_when_success(self, mock_s3_head):
        mock_s3_head.return_value = {
            "size": 12345,
            "content_type": "text/plain",
            "metadata": {"foo": "bar"},
        }

        response = self.client.patch(self.url, {"status": SUCCESS}, format="json")

        self.assertEqual(response.status_code, 200)
        mock_s3_head.assert_called_once_with(self.cloud_file.s3_key)

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.size, 12345)
        self.assertEqual(cf.content_type, "text/plain")
        self.assertEqual(cf.metadata, {"foo": "bar"})
        self.assertEqual(cf.status, SUCCESS)

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_empty_payload(self, mock_s3_head):
        response = self.client.patch(self.url, {}, format="json")

        self.assertEqual(response.status_code, 200)

        mock_s3_head.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.size, 500)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, PENDING)
        self.assertIsNone(cf.error_code)
        self.assertIsNone(cf.error_message)

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_does_not_sync_when_status_is_not_success(self, mock_s3_head):
        payload = {
            "status": FAILED,
            "error_code": "EntityTooLarge",
            "error_message": "Some error happened",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], CloudFileErrorCode.FILE_TOO_LARGE.value)

        mock_s3_head.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.size, 500)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, FAILED)

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_does_not_sync_when_file_is_not_found(self, mock_s3_head):
        mock_s3_head.return_value = None
        payload = {
            "status": SUCCESS,
            "error_message": "",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], CloudFileErrorCode.FILE_NOT_FOUND_IN_S3.value)

        mock_s3_head.assert_called_once()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.size, 500)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, FAILED)
        self.assertEqual(cf.error_code, CloudFileErrorCode.FILE_NOT_FOUND_IN_S3.value)
        self.assertEqual(cf.error_message, "File not found in storage during upload verification.")

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.delete_file_from_s3")
    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_does_not_sync_when_over_quota(self, mock_s3_head, mock_s3_delete_file_from_s3):
        limit_bytes = self.subscription.plan.max_storage_bytes

        mock_s3_head.return_value = {
            "size": limit_bytes + 1,
            "content_type": "text/plain",
            "metadata": {"foo": "bar"},
        }

        payload = {
            "status": SUCCESS,
            "error_message": "",
        }

        response = self.client.patch(self.url, payload, format="json")
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        mock_s3_head.assert_called_once()
        mock_s3_delete_file_from_s3.assert_called_once()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.content_type, "text/plain")
        self.assertEqual(cf.metadata, {"foo": "bar"})
        self.assertEqual(cf.status, FAILED)
        self.assertEqual(cf.error_code, CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value)
        self.assertEqual(cf.error_message, "User exceeded storage quota after final size verification.")

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.delete_file_from_s3")
    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_does_not_sync_when_status_is_not_success_unknown_error(self, mock_s3_head,
                                                                                   mock_s3_delete_file_from_s3):
        payload = {
            "status": FAILED,
            "error_code": "UnknownError",
            "error_message": "Some error happened",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], CloudFileErrorCode.UNKNOWN_S3_ERROR.value)

        mock_s3_head.assert_not_called()
        mock_s3_delete_file_from_s3.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.content_type, "aaa/ttt")
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, FAILED)
        self.assertEqual(cf.error_code, CloudFileErrorCode.UNKNOWN_S3_ERROR.value)
        self.assertEqual(cf.error_message, "Some error happened")

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.delete_file_from_s3")
    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_missing_status(self, mock_s3_head, mock_s3_delete_file_from_s3):
        limit_bytes = self.subscription.plan.max_storage_bytes

        mock_s3_head.return_value = {
            "size": limit_bytes + 1,
            "content_type": "text/plain",
            "metadata": {"foo": "bar"},
        }

        payload = {
            "error_message": "Some error happened",
        }

        response = self.client.patch(self.url, payload, format="json")
        self.assertIn("status", response.data)
        self.assertIn("error_message", response.data)
        self.assertEqual(response.data["status"], PENDING)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_s3_head.assert_not_called()
        mock_s3_delete_file_from_s3.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.status, PENDING)
        self.assertIsNone(cf.error_code)
        self.assertEqual(cf.error_message, "Some error happened")

    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.delete_file_from_s3")
    @patch("apps.cloud_storage.services.storage.s3_service.S3Service.head")
    def test_partial_update_not_success_missing_error_code(self, mock_s3_head, mock_s3_delete_file_from_s3):
        payload = {
            "error_message": "Some error happened",
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.data)
        self.assertIn("error_message", response.data)
        self.assertEqual(response.data["status"], PENDING)

        mock_s3_head.assert_not_called()
        mock_s3_delete_file_from_s3.assert_not_called()

        cf = CloudFile.objects.get(pk=self.cloud_file.pk)
        self.assertEqual(cf.metadata, {})
        self.assertEqual(cf.status, PENDING)
        self.assertIsNone(cf.error_code)
        self.assertEqual(cf.error_message, "Some error happened")
