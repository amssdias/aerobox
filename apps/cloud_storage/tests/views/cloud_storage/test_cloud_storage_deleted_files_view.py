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


class CloudStorageViewSetListDeletedFilesTests(APITestCase):

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
        cls.other_user_file_deleted = CloudFileFactory(
            user=cls.other_user, path="docs/other_user_file_deleted.txt"
        )

        cls.url = reverse("storage-deleted-files")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_deleted_files_only_from_authenticated_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)

        count_user_files = CloudFile.deleted.filter(user=self.user).count()
        self.assertEqual(response.data.get("count"), count_user_files)
        self.assertEqual(len(response.data.get("results")), count_user_files)

        returned_file_paths = [
            file["path"] for file in response.data.get("results")
        ]

        self.assertIn("docs/file2.txt", returned_file_paths)
        self.assertNotIn("docs/file1.txt", returned_file_paths)
        self.assertNotIn("docs/file3.txt", returned_file_paths)
        self.assertNotIn(
            "docs/other_user_file.txt", returned_file_paths
        )

    def test_list_excludes_not_deleted_files(self):
        response = self.client.get(self.url)
        returned_file_ids = [file["id"] for file in response.data.get("results")]

        self.assertNotIn(self.file1.id, returned_file_ids)
        self.assertNotIn(self.file3.id, returned_file_ids)

    def test_list_empty_if_no_deleted_files_exist(self):
        CloudFile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("results"), [])
        self.assertEqual(response.data.get("count"), 0)

    def test_list_deleted_files_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_deleted_files_pagination(self):
        """Ensure pagination works properly (if pagination is enabled)."""
        for i in range(20):  # Create more files to test pagination
            path = build_s3_path(
                user_id=self.user.id,
                file_name=f"docs/example_{i}.txt",
            )
            CloudFileFactory(user=self.user, path=path, deleted_at=timezone.now())

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        count_user_files = CloudFile.deleted.filter(user=self.user).count()
        self.assertEqual(response.data.get("count"), count_user_files)
        self.assertTrue("results" in response.data)
        self.assertEqual(len(response.data.get("results")), count_user_files)

    def test_list_deleted_files_filters_files_by_user_only(self):
        response = self.client.get(self.url)
        returned_file_ids = [file["id"] for file in response.data.get("results")]

        self.assertNotIn(self.other_user_file_deleted.id, returned_file_ids)

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
                "deleted_at",
            }
            self.assertTrue(expected_fields.issubset(sample_file.keys()))

    def test_list_works_with_large_datasets(self):
        CloudFile.objects.all().delete()  # Clear existing records
        total_files = 1000
        for i in range(total_files):
            CloudFileFactory(user=self.user, path=f"big_file_{i}.txt", deleted_at=timezone.now())

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        page_size = CloudFilesPagination.page_size
        self.assertEqual(response.data.get("count"), total_files)
        self.assertEqual(len(response.data.get("results")), page_size)
