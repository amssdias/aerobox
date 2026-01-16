from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED, PENDING
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.cloud_storage.utils.path_utils import build_s3_path, build_object_path
from apps.users.factories.user_factory import UserFactory


class UpdateFileIntegrationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="user1", password="password123")

        cls.file = CloudFileFactory(
            user=cls.user,
            file_name="file1.txt",
            path="file1.txt",
            status=SUCCESS,
            size=999,
        )

        cls.folder = FolderFactory(user=cls.user)

        # URL for renaming
        cls.url = reverse("storage-detail", kwargs={"pk": cls.file.pk})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_successful_file_rename(self):
        response = self.client.put(self.url, {"file_name": "renamed"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.file_name, "renamed.txt")

        self.assertEqual(self.file.path, "renamed.txt")

    def test_put_allows_file_name_with_internal_dots(self):
        response = self.client.put(self.url, {"file_name": "renamed.with.dots"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.file_name, "renamed.with.dots.txt")

        self.assertEqual(self.file.path, "renamed.with.dots.txt")

    def test_put_rejects_file_name_with_only_dots(self):
        response = self.client.put(self.url, {"file_name": "..."}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_put_rejects_file_name_starting_with_dot(self):
        response = self.client.put(self.url, {"file_name": ".renamed.with.dots"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_put_rejects_file_name_ending_with_dot(self):
        response = self.client.put(self.url, {"file_name": "renamed.with.dots."}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_successful_update_file_folder(self):
        data = {
            "file_name": "test1",
            "folder": self.folder.id,
        }
        response = self.client.put(self.url, data, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.folder.id, self.folder.id)
        self.assertEqual(self.file.file_name, "test1.txt")
        self.assertEqual(self.file.path, build_object_path(self.file.file_name, self.file.folder))

    def test_update_with_invalid_folder(self):
        data = {
            "folder": 9999
        }
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("folder", response.data)

    def test_put_rejects_folder_not_owned_by_user(self):
        user = UserFactory(username="user2", password="password123")
        folder = FolderFactory(user=user)
        data = {
            "folder": folder.id
        }
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("folder", response.data)

    def test_update_with_null_folder(self):
        data = {
            "file_name": self.file.file_name,
            "folder": None
        }
        response = self.client.put(self.url, data, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self.file.folder)

    def test_update_with_blank_file_name(self):
        data = {
            "file_name": "",
            "folder": self.folder.id
        }
        current_file_name = self.file.file_name
        response = self.client.put(self.url, data, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)
        self.assertEqual(self.file.file_name, current_file_name)

    def test_update_with_null_file_name(self):
        data = {
            "file_name": None,
            "folder": self.folder.id
        }
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_update_with_missing_file_name(self):
        folder = FolderFactory(user=self.user)
        data = {
            "folder": folder.id
        }
        response = self.client.put(self.url, data, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(self.file.folder.id, folder.id)

    def test_update_file_name_only(self):
        new_name = "updated_name"
        data = {
            "file_name": new_name
        }
        response = self.client.put(self.url, data, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.file_name, "updated_name.txt")

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

    def test_cannot_rename_non_existent_file(self):
        non_existent_url = reverse("storage-detail", kwargs={"pk": 999})
        response = self.client.put(
            non_existent_url, {"file_name": "non_existent"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_correct_response_message_on_successful_rename(self):
        response = self.client.put(
            self.url, {"file_name": "renamed_file"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "File successfully updated.")

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
        url = reverse("storage-detail", kwargs={"pk": file.pk})
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
        url = reverse("storage-detail", kwargs={"pk": file.pk})
        response = self.client.put(url, {"file_name": "fixed_name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_rename_with_same_name(self):
        response = self.client.put(
            self.url, {"file_name": self.file.file_name.split(".")[0]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_cannot_rename_to_too_long_name(self):
        """Test renaming a file with an excessively long name should fail."""
        long_name = "a" * 256
        response = self.client.put(self.url, {"file_name": long_name}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_name", response.data)

    def test_rename_preserves_file_extension(self):
        response = self.client.put(self.url, {"file_name": "new_name"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.file.file_name.endswith(".txt"))

    def test_put_does_nothing_when_no_fields_are_provided(self):
        file_name = self.file.file_name
        self.file.folder = None
        self.file.save()

        response = self.client.put(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.file.refresh_from_db()

        self.assertEqual(self.file.file_name, file_name)
        self.assertIsNone(self.file.folder)

    def test_put_ignores_unallowed_fields_like_path(self):
        response = self.client.put(self.url, {"file_name": "new_name", "path": "docs/wrongpath"}, format="json")
        self.file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.path, "new_name.txt")

    def test_put_ignores_unallowed_fields_like_size(self):
        response = self.client.put(self.url, {"file_name": "new_name", "size": 123}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.file.size, 999)
