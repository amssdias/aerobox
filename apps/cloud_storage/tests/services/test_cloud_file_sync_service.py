from unittest.mock import patch

from django.test import TestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.services.storage.cloud_file_sync_service import CloudFileSyncService
from apps.users.factories.user_factory import UserFactory


class CloudFileSyncServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")

    def setUp(self):
        self.cloud_file = CloudFileFactory(
            file_name="file1.txt",
            path="folder1",
            size=500,
            content_type="aaa/ttt",
            user=self.user,
        )

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_sync_updates_fields_from_s3(self, mock_s3_head):
        mock_s3_head.return_value = {
            "size": 500,
            "content_type": "text/plain",
            "metadata": {"foo": "bar"},
        }

        service = CloudFileSyncService()
        instance, size_changed = service.sync(self.cloud_file)

        mock_s3_head.assert_called_once_with(self.cloud_file.s3_key)

        self.assertIs(instance, self.cloud_file)
        self.assertFalse(size_changed)

        self.cloud_file.refresh_from_db()
        self.assertEqual(self.cloud_file.size, 500)
        self.assertEqual(self.cloud_file.content_type, "text/plain")
        self.assertEqual(self.cloud_file.metadata, {"foo": "bar"})

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_sync_uses_empty_metadata_when_missing(self, mock_s3_head):
        mock_s3_head.return_value = {
            "size": 10,
            "content_type": "image/png",
        }

        service = CloudFileSyncService()
        service.sync(self.cloud_file)

        self.cloud_file.refresh_from_db()
        self.assertEqual(self.cloud_file.size, 10)
        self.assertEqual(self.cloud_file.content_type, "image/png")
        self.assertEqual(self.cloud_file.metadata, {})

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_sync_overwrites_existing_values(self, mock_s3_head):
        self.cloud_file.size = 1
        self.cloud_file.content_type = "application/json"
        self.cloud_file.metadata = {"old": "value"}
        self.cloud_file.save()

        mock_s3_head.return_value = {
            "size": 999,
            "content_type": "application/pdf",
            "metadata": {"new": "value"},
        }

        service = CloudFileSyncService()
        service.sync(self.cloud_file)

        self.cloud_file.refresh_from_db()
        self.assertEqual(self.cloud_file.size, 999)
        self.assertEqual(self.cloud_file.content_type, "application/pdf")
        self.assertEqual(self.cloud_file.metadata, {"new": "value"})

    @patch("apps.cloud_storage.services.storage.cloud_file_sync_service.S3Service.head")
    def test_sync_returns_size_changed_true(self, mock_s3_head):
        self.cloud_file.size = 1
        self.cloud_file.content_type = "application/json"
        self.cloud_file.metadata = {"old": "value"}
        self.cloud_file.save()

        mock_s3_head.return_value = {
            "size": 999,
            "content_type": "application/pdf",
            "metadata": {"new": "value"},
        }

        service = CloudFileSyncService()
        instance, size_changed = service.sync(self.cloud_file)

        self.cloud_file.refresh_from_db()
        self.assertTrue(size_changed)
