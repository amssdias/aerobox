import unittest
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.exceptions import FileUploadError
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services.storage.s3_service import S3Service
from apps.cloud_storage.utils.path_utils import build_object_path
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class CloudStoragePresignedURLTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", password="testpass")
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
        cls.folder = FolderFactory(user=cls.user)
        cls.url = reverse("storage-list")

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.data = {
            "file_name": "test-image.png",
            "folder": self.folder.id,
            "size": 100,
            "content_type": "image/png",
        }

    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    def test_create_file_and_presigned_url_success(self, mock_s3):
        """Test generating a presigned URL successfully."""

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("presigned-url", response.data)
        self.assertIn("file", response.data)
        self.assertIn("id", response.data.get("file"))
        self.assertIn("file_name", response.data.get("file"))
        self.assertIn("size", response.data.get("file"))
        self.assertIn("content_type", response.data.get("file"))
        self.assertIn("path", response.data.get("file"))
        self.assertEqual(response.data["presigned-url"]["url"], "https://s3-presigned-url.com")
        self.assertIn("fields", response.data.get("presigned-url"))

        mock_s3.assert_called_once()

    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    def test_create_file_with_multiple_dots_on_file_name_and_presigned_url_success(self, mock_s3):
        self.data["file_name"] = "test.image.png"
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("presigned-url", response.data)
        self.assertIn("file", response.data)
        self.assertIn("id", response.data.get("file"))
        self.assertIn("file_name", response.data.get("file"))
        self.assertIn("size", response.data.get("file"))
        self.assertIn("content_type", response.data.get("file"))
        self.assertIn("path", response.data.get("file"))
        self.assertEqual(response.data["presigned-url"]["url"], "https://s3-presigned-url.com")
        self.assertIn("fields", response.data.get("presigned-url"))

        mock_s3.assert_called_once()
        self.assertTrue(CloudFile.objects.get(file_name=self.data["file_name"]))

    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    @patch("apps.cloud_storage.views.cloud_storage.generate_unique_hash")
    def test_generate_unique_hash_called_on_file_creation(self, mock_generate_unique_hash, mock_s3):
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("presigned-url", response.data)
        self.assertIn("file", response.data)
        self.assertIn("id", response.data.get("file"))
        self.assertIn("file_name", response.data.get("file"))
        self.assertIn("size", response.data.get("file"))
        self.assertIn("content_type", response.data.get("file"))
        self.assertIn("path", response.data.get("file"))
        self.assertEqual(response.data["presigned-url"]["url"], "https://s3-presigned-url.com")
        self.assertIn("fields", response.data.get("presigned-url"))

        mock_s3.assert_called_once()
        mock_generate_unique_hash.assert_called_once()

    def test_create_file_and_presigned_url_requires_authentication(self):
        self.client.logout()
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch.object(S3Service, "create_presigned_post_url", return_value=None)
    def test_create_file_and_presigned_url_s3_error(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], str(FileUploadError.default_detail))

    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    def test_create_file_and_presigned_url_creates_database_entry(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        path = build_object_path(
            file_name=self.data.get('file_name'),
            folder=self.folder,
        )
        cloud_file = CloudFile.objects.filter(user=self.user, path=path)
        self.assertTrue(cloud_file.exists())
        self.assertEqual(cloud_file.first().folder.id, self.folder.id)

    def test_create_file_and_presigned_url_with_long_filename(self):
        self.data["file_name"] = "file" + ("a" * 255) + ".jpg"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_create_file_with_name_starting_with_dot(self):
        self.data["file_name"] = ".file.jpg"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_create_file_with_name_ending_with_dot(self):
        self.data["file_name"] = "file.jpg."
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_create_file_with_name_only_dots(self):
        self.data["file_name"] = "..."
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_create_file_with_name_only_extension(self):
        self.data["file_name"] = ".jpg"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    @unittest.skip("Skipping: Forbidden file type validation not implemented yet.")
    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    def test_create_file_and_presigned_url_forbidden_file_type(self, mock_s3):
        """Test rejecting an upload of a forbidden file type (e.g., `.bat`)."""
        data = {"path": "uploads/malicious.bat"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_file_and_presigned_url_no_json_body(self):
        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_file_and_presigned_url_invalid_json_structure(self):
        data = {"invalid_key": "uploads/test.txt"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(S3Service, "create_presigned_post_url", return_value=None)
    def test_create_file_and_presigned_url_s3_connection_error(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], str(FileUploadError.default_detail))

    @patch.object(
        S3Service,
        "create_presigned_post_url",
        return_value={"url": "https://s3-presigned-url.com", "fields": {}},
    )
    def test_create_file_and_presigned_url_with_subdirectories(self, mock_s3):
        folder = FolderFactory(user=self.user, parent=self.folder)
        self.data["folder"] = folder.id
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        file_path = build_object_path(folder=folder, file_name=self.data.get("file_name"))
        self.assertEqual(response.data.get("file").get("path"), file_path)

    def test_rejects_file_when_exceeds_plan_storage_limit(self):
        max_storage_bytes = self.subscription.plan.max_storage_bytes

        self.data["size"] = max_storage_bytes + 1

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("size", response.data)
