from unittest.mock import Mock, patch

from django.test import TestCase

from apps.cloud_storage.constants.cloud_files import USER_PREFIX
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.users.factories.user_factory import UserFactory


class CloudFilesSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.serializer = CloudFilesSerializer
        cls.user = UserFactory(username="testuser")
        cls.request = Mock()
        cls.request.user = cls.user
        cls.context = {"request": cls.request}

    def test_valid_file_creation(self):
        data = {
            "file_name": "document.pdf",
            "path": "uploads",
            "size": 1024,
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_file_name_with_slash(self):
        data = {"file_name": "invalid/name.pdf", "path": "uploads"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_invalid_file_name_with_backslash(self):
        data = {"file_name": "invalid\\name.pdf", "path": "uploads"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_empty_file_name(self):
        data = {"file_name": "   ", "path": "uploads"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("file_name", serializer.errors)

    def test_valid_path(self):
        data = {
            "file_name": "image.png",
            "path": "pictures",
            "size": 5000,
            "content_type": "image/png",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_path_starting_with_slash(self):
        data = {"file_name": "image.png", "path": "/invalid/path"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

    def test_invalid_path_ending_with_slash(self):
        data = {"file_name": "image.png", "path": "invalid/path/"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

    def test_invalid_path_starting_and_ending_with_slash(self):
        data = {"file_name": "image.png", "path": "/invalid/path/"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

    def test_invalid_path_duplicate_slash(self):
        data = {"file_name": "image.png", "path": "invalid//path/"}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

        data["path"] = "//invalid/path"
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

        data["path"] = "invalid/path//"
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

    def _test_missing_user_context(self):
        invalid_context = {"request": Mock(user=None)}
        data = {
            "file_name": "test.txt",
            "path": "docs",
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=invalid_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_incorrect_content_type(self):
        data = {
            "file_name": "image.jpg",
            "path": "photos",
            "size": 2048,
            "content_type": "application/json",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_valid_relative_path_method(self, mock_create_customer):
        cloud_file = CloudFileFactory(
            file_name="test.txt",
            path="docs",
            size=500,
            content_type="text/plain",
        )
        serializer = self.serializer(instance=cloud_file, context=self.context)
        self.assertEqual(
            serializer.data["relative_path"], cloud_file.get_relative_path()
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
        self.assertFalse(serializer.is_valid(), serializer.errors)

    def test_missing_size(self):
        data = {
            "file_name": "test.pdf",
            "path": "uploads",
            "content_type": "application/pdf",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_missing_content_type(self):
        data = {"file_name": "test.pdf", "path": "uploads", "size": 1024}
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("content_type", serializer.errors)

    def test_large_file_size(self):
        data = {
            "file_name": "largefile.bin",
            "path": "backups",
            "size": 2**30,
            "content_type": "application/octet-stream",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def _test_extremely_large_file_size(self):
        data = {
            "file_name": "hugefile.bin",
            "path": "backups",
            "size": 2**40,
            "content_type": "application/octet-stream",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("size", serializer.errors)

    def test_duplicate_file_name_in_same_path(self):
        CloudFileFactory(
            file_name="duplicate.txt",
            path="folder1",
            size=500,
            content_type="text/plain",
            user=self.user,
        )
        data = {
            "file_name": "duplicate.txt",
            "path": "folder2",
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_file_name_in_same_path_rejected(self):
        user_prefix = USER_PREFIX.format(self.user.id)
        file_name = "duplicate.txt"
        path = "folder1"
        data = {
            "file_name": file_name,
            "path": f"{user_prefix}/{path}/{file_name}",
            "size": 500,
            "content_type": "text/plain",
            "user": self.user,
        }

        CloudFileFactory(**data)

        data["path"] = path
        serializer = self.serializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("path", serializer.errors)

    def test_special_characters_in_file_name(self):
        data = {
            "file_name": "my@file#name!.txt",
            "path": "uploads",
            "size": 500,
            "content_type": "text/plain",
        }
        serializer = self.serializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
