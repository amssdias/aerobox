from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class CloudFilesSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.serializer = CloudFilesSerializer
        cls.user = UserFactory(username="testuser")
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
        cls.request = Mock()
        cls.request.user = cls.user
        cls.context = {"request": cls.request}
        cls.folder = FolderFactory(user=cls.user)

    def test_valid_file_creation(self):
        data = {
            "file_name": "document.pdf",
            "size": 1024,
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_file_name_with_multiple_dots(self):
        data = {
            "file_name": "file.name.pdf",
            "size": 1024,
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid())

    def test_invalid_file_name_starting_with_dots(self):
        data = {"file_name": ".filename.pdf"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_ending_with_dots(self):
        data = {"file_name": "filename.pdf."}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_with_only_extension(self):
        data = {"file_name": ".pdf"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_with_only_dots(self):
        data = {"file_name": "..."}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_with_slash(self):
        data = {"file_name": "invalid/name.pdf"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_with_backslash(self):
        data = {"file_name": "invalid\\name.pdf"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_empty_file_name(self):
        data = {"file_name": "   "}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_path_not_used(self):
        data = {
            "file_name": "image.png",
            "path": "pictures",
            "size": 5000,
            "content_type": "image/png",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get("path"))

    def test_valid_folder(self):
        data = {
            "file_name": "image.png",
            "folder": self.folder.id,
            "size": 5000,
            "content_type": "image/png",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_folder_different_user(self):
        user = UserFactory(username="testuser-1")
        folder = FolderFactory(user=user)
        data = {
            "file_name": "image.png",
            "folder": folder.id,
            "size": 5000,
            "content_type": "image/png",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid(), serializer.errors)

    def test_missing_user_context(self):
        invalid_context = {"request": Mock(user=None)}
        data = {
            "file_name": "test.txt",
            "path": "docs",
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=invalid_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_incorrect_content_type(self):
        data = {
            "file_name": "image.jpg",
            "size": 2048,
            "content_type": "application/json",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_valid_path_method(self, mock_create_customer):
        cloud_file = CloudFileFactory(
            file_name="test.txt",
            path="docs",
            size=500,
            content_type="text/plain",
        )
        serializer = self.serializer(instance=cloud_file, context=self.context)
        self.assertEqual(
            serializer.data["path"], cloud_file.path
        )

    def test_missing_file_name(self):
        data = {"path": "documents", "size": 1000, "content_type": "application/pdf"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_missing_path(self):
        data = {
            "file_name": "test.pdf",
            "size": 1000,
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid())

    def test_missing_size(self):
        data = {
            "file_name": "test.pdf",
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_missing_content_type(self):
        data = {"file_name": "test.pdf", "size": 1024}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("content_type", serializer.errors)

    def test_large_file_size(self):
        max_bytes = self.subscription.plan.max_file_upload_size_bytes
        data = {
            "file_name": "largefile.bin",
            "size": max_bytes + 1,
            "content_type": "application/octet-stream",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())

    def test_extremely_large_file_size(self):
        max_bytes = self.subscription.plan.max_file_upload_size_bytes
        data = {
            "file_name": "hugefile.bin",
            "path": "backups",
            "size": max_bytes + 1,
            "content_type": "application/octet-stream",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_duplicate_file_name_in_same_path(self):
        CloudFileFactory(
            file_name="duplicate.txt",
            folder=self.folder,
            path="folder1",
            size=500,
            content_type="text/plain",
            user=self.user,
        )
        data = {
            "file_name": "duplicate.txt",
            "folder": self.folder.id,
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_special_characters_in_file_name(self):
        data = {
            "file_name": "my@file#name!.txt",
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_size_rejects_when_exceeds_storage_limit(self):
        size_in_bytes = 5_000 * 1000 * 1000
        CloudFileFactory(user=self.user, size=size_in_bytes)

        data = {
            "file_name": "document.pdf",
            "size": 10 * 1000 * 1000,
            "content_type": "application/pdf",
        }

        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_validate_size_rejects_when_exceeds_file_size_limit(self):
        size_in_bytes = 4_000 * 1000 * 1000
        CloudFileFactory(user=self.user, size=size_in_bytes)

        data = {
            "file_name": "document.pdf",
            "size": 201 * 1000 * 1000,
            "content_type": "application/pdf",
        }

        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)


    def test_validate_size_allows_exactly_at_limit(self):
        size_in_bytes = 4_800 * 1000 * 1000
        CloudFileFactory(user=self.user, size=size_in_bytes)

        data = {
            "file_name": "document.pdf",
            "size": 2_00 * 1000 * 1000,
            "content_type": "application/pdf",
        }

        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid())

    def test_validate_size_raises_when_no_active_subscription(self):
        subscription = self.user.subscriptions.filter(status=SubscriptionStatusChoices.ACTIVE.value).first()
        subscription.status = SubscriptionStatusChoices.INACTIVE.value
        subscription.save()

        data = {
            "file_name": "document.pdf",
            "size": 1_000 * 1000 * 1000,
            "content_type": "application/pdf",
        }

        serializer = self.serializer(data=data, context=self.context)

        with self.assertRaises(ValidationError) as exc:
            serializer.validate_size(1_000)
        assert "no active subscription" in str(exc.exception).lower()
