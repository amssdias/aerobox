import unittest
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.exceptions import FileUploadError
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.users.factories.user_factory import UserFactory


class CloudStoragePresignedURLTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", password="testpass")
        cls.url = reverse("storage-list")

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.data = {
            "file_name": "test-image.png",
            "path": "uploads",
            "size": 12343,
            "content_type": "image/png",
        }

    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_success(self, mock_s3):
        """Test generating a presigned URL successfully."""

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("presigned-url", response.data)
        self.assertIn("id", response.data)
        self.assertIn("file_name", response.data)
        self.assertIn("size", response.data)
        self.assertIn("content_type", response.data)
        self.assertIn("relative_path", response.data)
        self.assertEqual(response.data["presigned-url"], "https://s3-presigned-url.com")

        path = build_s3_path(
            self.user.id, f"{self.data.get('path')}/{self.data.get('file_name')}"
        )
        mock_s3.assert_called_once_with(object_name=path)

    def test_create_file_and_presigned_url_requires_authentication(self):
        self.client.logout()
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_file_and_presigned_url_missing_path(self):
        """Test that missing 'path' field returns a 400 error."""
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("path", response.data)

    def test_create_file_and_presigned_url_invalid_path(self):
        self.data["path"] = "/"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.data["path"] = "folder1/"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.data["path"] = "/folder1"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.data["path"] = "folder1//folder2"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(S3Service, "generate_presigned_upload_url", return_value=None)
    def test_create_file_and_presigned_url_s3_error(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], str(FileUploadError.default_detail))

    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_creates_database_entry(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        path = build_s3_path(
            self.user.id,
            f"{self.data.get('path')}/{self.data.get('file_name')}",
        )
        self.assertTrue(CloudFile.objects.filter(user=self.user, path=path).exists())

    def test_create_file_and_presigned_url_invalid_file_extension(self):
        self.data["path"] = "uploads/malware.exe"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "The file path cannot contain dots (`.`). Dots are only allowed in file names for extensions.",
            response.data.get("path"),
        )

    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_with_special_characters(self, mock_s3):
        self.data["path"] = "uploads/special-@#$.png"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("path", response.data)
        self.assertIn(
            "The file path cannot contain dots (`.`). Dots are only allowed in file names for extensions.",
            response.data.get("path"),
        )

    def test_create_file_and_presigned_url_with_long_filename(self):
        self.data["file_name"] = "file" + ("a" * 255) + ".jpg"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_uppercase_path(self, mock_s3):
        self.data["path"] = "uploads/FOLDER1"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("file_name", response.data)
        self.assertIn("size", response.data)
        self.assertIn("content_type", response.data)
        self.assertIn("relative_path", response.data)

        path = "/".join(response.data.get("relative_path").split("/")[:2])
        self.assertEqual(self.data.get("path").lower(), path)

    @unittest.skip("Skipping: Forbidden file type validation not implemented yet.")
    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
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

    @patch.object(S3Service, "generate_presigned_upload_url", return_value=None)
    def test_create_file_and_presigned_url_s3_connection_error(self, mock_s3):
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], str(FileUploadError.default_detail))

    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_with_subdirectories(self, mock_s3):
        self.data["path"] = "uploads/folder1/folder2"
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @unittest.skip(
        "Skipping: Special character handling in presigned URLs not implemented yet."
    )
    @patch.object(
        S3Service,
        "generate_presigned_upload_url",
        return_value="https://s3-presigned-url.com",
    )
    def test_create_file_and_presigned_url_special_unicode_characters(self, mock_s3):
        data = {"path": "uploads/测试文件📁"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
