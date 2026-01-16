from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.users.factories.user_factory import UserFactory


class CloudStorageRestoreDeletedFileTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser1")
        cls.token, _ = Token.objects.get_or_create(user=cls.user)

        cls.other_user = UserFactory(email="other@test.com")

        # Active file (not deleted)
        cls.active_file = CloudFileFactory(
            user=cls.user,
            file_name="active_file.pdf",
            deleted_at=None
        )

        # Deleted file of another user
        cls.other_user_file = CloudFileFactory(
            user=cls.other_user,
            file_name="foreign_file.pdf",
            deleted_at=timezone.now()
        )

        cls.url_active_file = reverse("storage-restore-deleted-file", args=[cls.active_file.id])

    def setUp(self):
        self.deleted_file = CloudFileFactory(
            user=self.user,
            file_name="deleted_file.pdf",
            deleted_at=timezone.now()
        )
        self.url = reverse("storage-restore-deleted-file", args=[self.deleted_file.id])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_restore_deleted_file_successfully(self):
        response = self.client.patch(self.url)
        self.deleted_file.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self.deleted_file.deleted_at)
        self.assertEqual(response.data, {"id": self.deleted_file.id, "restored": True})

    def test_restore_file_not_deleted_returns_404(self):
        response = self.client.patch(self.url_active_file)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_restore_deleted_file_requires_authentication(self):
        self.client.logout()
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_restore_other_users_file(self):
        url = reverse("storage-restore-deleted-file", args=[self.other_user_file.id])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_data_contains_id_and_restored_flag(self):
        response = self.client.patch(self.url)

        self.assertIn("id", response.data)
        self.assertIn("restored", response.data)
        self.assertTrue(response.data["restored"])

    def test_deleted_at_is_not_modified_on_failed_restore(self):
        before = self.active_file.deleted_at
        self.client.patch(self.url_active_file)

        self.active_file.refresh_from_db()
        self.assertEqual(self.active_file.deleted_at, before)

    def test_restore_file_does_not_affect_other_files(self):
        deleted_file_1 = CloudFileFactory(
            user=self.user,
            file_name="deleted_file_1.pdf",
            deleted_at=timezone.now()
        )
        self.client.patch(self.url)

        deleted_file_1.refresh_from_db()
        self.assertTrue(deleted_file_1.deleted_at)

    def test_restore_deleted_file_twice(self):
        # First restore
        response1 = self.client.patch(self.url)

        # Second restore
        response2 = self.client.patch(self.url)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_restore_with_invalid_id(self):
        url = reverse("storage-restore-deleted-file", args=[999999])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_restore_deleted_file_returns_expected_status_and_data(self):
        response = self.client.patch(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.deleted_file.id)
        self.assertTrue(response.data["restored"])
