from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.pagination import CloudFilesPagination
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.users.factories.user_factory import UserFactory


class CloudStorageViewSetListTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", password="password")
        cls.token, _ = Token.objects.get_or_create(user=cls.user)
        cls.other_user = UserFactory(username="otheruser", password="password")

        # Create files for the authenticated user
        cls.file1 = CloudFileFactory(user=cls.user, path="docs/file1.txt")
        cls.file2 = CloudFileFactory(
            user=cls.user, path="docs/file2.txt", deleted_at=timezone.now()
        )
        cls.file3 = CloudFileFactory(user=cls.user, path="docs/file3.txt")

        # Create a file for another user (should not appear in results)
        cls.other_user_file = CloudFileFactory(
            user=cls.other_user, path="docs/other_user_file.txt"
        )

        cls.url = reverse("storage-list")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_returns_only_authenticated_user_files(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)

        count_user_files = CloudFile.not_deleted.filter(user=self.user).count()
        self.assertEqual(response.data.get("count"), count_user_files)
        self.assertEqual(len(response.data.get("results")), count_user_files)

        returned_file_paths = [
            file["path"] for file in response.data.get("results")
        ]

        self.assertIn("docs/file1.txt", returned_file_paths)
        self.assertIn("docs/file3.txt", returned_file_paths)
        self.assertNotIn(
            "docs/other_user_file.txt", returned_file_paths
        )  # Belongs to another user
        self.assertNotIn("docs/file2.txt", returned_file_paths)  # Soft-deleted

    def test_list_excludes_soft_deleted_files(self):
        response = self.client.get(self.url)
        returned_file_ids = [file["id"] for file in response.data.get("results")]

        self.assertNotIn(self.file2.id, returned_file_ids)

    def test_list_empty_if_no_files_exist(self):
        CloudFile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("results"), [])
        self.assertEqual(response.data.get("count"), 0)

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_pagination(self):
        """Ensure pagination works properly (if pagination is enabled)."""
        for i in range(20):  # Create more files to test pagination
            path = build_s3_path(
                user_id=self.user.id,
                file_name=f"docs/example_{i}.txt",
            )
            CloudFileFactory(user=self.user, path=path)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        count_user_files = CloudFile.not_deleted.filter(user=self.user).count()
        self.assertEqual(response.data.get("count"), count_user_files)
        self.assertTrue("results" in response.data)
        self.assertEqual(len(response.data.get("results")), count_user_files)

    def test_list_filters_files_by_user_only(self):
        response = self.client.get(self.url)
        returned_file_ids = [file["id"] for file in response.data.get("results")]

        self.assertNotIn(self.other_user_file.id, returned_file_ids)

    def test_list_works_with_multiple_users(self):
        response = self.client.get(self.url)
        returned_file_paths = [
            file["path"] for file in response.data.get("results")
        ]

        self.assertIn("docs/file1.txt", returned_file_paths)
        self.assertIn("docs/file3.txt", returned_file_paths)
        self.assertNotIn("docs/other_user_file.txt", returned_file_paths)

    def test_list_returns_correct_fields(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if response.data.get("results"):
            sample_file = response.data.get("results")[0]
            expected_fields = {
                "id",
                "file_name",
                "size",
                "content_type",
                "path",
                "created_at",
            }
            self.assertTrue(expected_fields.issubset(sample_file.keys()))

    def test_list_works_with_large_datasets(self):
        CloudFile.objects.all().delete()  # Clear existing records
        total_files = 1000
        for i in range(total_files):
            CloudFileFactory(user=self.user, path=f"big_file_{i}.txt")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        page_size = CloudFilesPagination.page_size
        self.assertEqual(response.data.get("count"), total_files)
        self.assertEqual(len(response.data.get("results")), page_size)

    def test_list_does_not_include_deleted_files_in_large_datasets(self):
        CloudFile.objects.all().delete()  # Clear existing records

        # Create 500 active files and 500 soft-deleted files
        for i in range(500):
            CloudFileFactory(user=self.user, path=f"active_file_{i}.txt")
            CloudFileFactory(
                user=self.user, path=f"deleted_file_{i}.txt", deleted_at=timezone.now()
            )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 500)

        page_size = CloudFilesPagination.page_size
        self.assertEqual(len(response.data.get("results")), page_size)
