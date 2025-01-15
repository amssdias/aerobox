import unittest
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED, PENDING
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.users.factories.user_factory import UserFactory


class RenameFileIntegrationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="user1", password="password123")

        # Create file for the authenticated user
        cls.path_1 = build_s3_path(
            user_id=cls.user.id,
            file_name="docs/file1.txt",
        )

        cls.file = CloudFileFactory(
            user=cls.user,
            file_name="file1.txt",
            path=cls.path_1,
            status=SUCCESS,
        )

        # URL for renaming
        cls.url = reverse("storage-rename-file", kwargs={"pk": cls.file.pk})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    @patch.object(S3Service, "rename_file", return_value=True)
    def test_successful_file_rename(self, mock_s3_rename):
        response = self.client.put(self.url, {"file_name": "renamed"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.file_name, "renamed.txt")

        path = build_s3_path(
            user_id=self.user.id,
            file_name="docs/renamed.txt",
        )
        self.assertEqual(self.file.path, path)
        mock_s3_rename.assert_called_once()

    def test_unauthenticated_user_cannot_rename(self):
        self.client.logout()
        response = self.client.put(
            self.url, {"file_name": "new_name.txt"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_rename_other_users_file(self):
        self.client.logout()
        other_user = UserFactory(username="user2", password="password123")
        self.client.force_authenticate(user=other_user)
        response = self.client.put(
            self.url, {"file_name": "new_name.txt"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_rename_to_empty_name(self):
        response = self.client.put(self.url, {"file_name": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_cannot_rename_with_invalid_characters(self):
        response = self.client.put(
            self.url, {"file_name": "invalid/name"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(
            str(response.data.get("file_name")[0]),
            "The file name cannot contain '/' or '\\'.",
        )

        response = self.client.put(
            self.url, {"file_name": "invalid\\name"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(
            str(response.data.get("file_name")[0]),
            "The file name cannot contain '/' or '\\'.",
        )

        response = self.client.put(
            self.url, {"file_name": "invalid/name.txt"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(
            str(response.data.get("file_name")[0]),
            "The file name cannot contain '/' or '\\'.",
        )

    def test_cannot_rename_with_extension(self):
        response = self.client.put(self.url, {"file_name": "name.txt"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(
            str(response.data.get("file_name")[0]),
            "The file name cannot contain '.' or extensions.",
        )

    def test_cannot_rename_non_existent_file(self):
        non_existent_url = reverse("storage-rename-file", kwargs={"pk": 999})
        response = self.client.put(
            non_existent_url, {"file_name": "new_name.txt"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch.object(S3Service, "rename_file", return_value=False)
    def test_s3_rename_failure_returns_error(self, mock_s3_rename):
        response = self.client.put(self.url, {"file_name": "renamed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_s3_rename.assert_called_once()

    @patch.object(S3Service, "rename_file", return_value=True)
    def test_correct_response_message_on_successful_rename(self, mock_s3_rename):
        response = self.client.put(
            self.url, {"file_name": "renamed_file"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "File renamed to renamed_file.txt")

    def test_cannot_rename_failed_upload(self):
        path = build_s3_path(
            user_id=self.user.id,
            file_name="docs/file2.txt",
        )
        file = CloudFileFactory(
            user=self.user,
            file_name="file2.txt",
            path=path,
            status=FAILED,
        )
        url = reverse("storage-rename-file", kwargs={"pk": file.pk})
        response = self.client.put(url, {"file_name": "fixed_name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_rename_pending_upload_file(self):
        path = build_s3_path(
            user_id=self.user.id,
            file_name="docs/file3.txt",
        )
        file = CloudFileFactory(
            user=self.user,
            file_name="file3.txt",
            path=path,
            status=PENDING,
        )
        url = reverse("storage-rename-file", kwargs={"pk": file.pk})
        response = self.client.put(url, {"file_name": "fixed_name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_rename_with_same_name(self):
        """Test renaming a file to the same name should fail."""
        response = self.client.put(
            self.url, {"file_name": self.file.file_name.split(".")[0]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(
            str(response.data.get("file_name")[0]),
            "The new file name cannot be the same as the current file name.",
        )

    def test_cannot_rename_to_too_long_name(self):
        """Test renaming a file with an excessively long name should fail."""
        long_name = "a" * 256
        response = self.client.put(self.url, {"file_name": long_name}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    @unittest.skip("Skipping: Unsupported extensions not implemented yet.")
    def test_cannot_rename_to_unsupported_extension(self):
        """Test renaming a file to an unsupported extension should fail."""
        response = self.client.put(
            self.url, {"file_name": "new_name.exe"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(S3Service, "rename_file", return_value=True)
    def test_rename_preserves_file_extension(self, mock_s3_rename):
        response = self.client.put(self.url, {"file_name": "new_name"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.file.file_name.endswith(".txt"))

    def test_cannot_rename_without_required_field(self):
        response = self.client.put(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
