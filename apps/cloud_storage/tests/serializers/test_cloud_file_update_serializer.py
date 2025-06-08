from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from rest_framework.exceptions import ValidationError

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers.cloud_files import CloudFileUpdateSerializer
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CloudFileUpdateSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = UserFactory(username="testuser")
        cls.folder = FolderFactory(user=cls.user)
        cls.file = CloudFileFactory(file_name="document.txt", folder=cls.folder, user=cls.user)
        cls.serializer = CloudFileUpdateSerializer

    def get_context(self):
        request = self.factory.post("/fake-url/")
        request.user = self.user
        return {"request": request}

    def test_rename_file_valid(self):
        data = {"file_name": "updated_name"}
        serializer = self.serializer(instance=self.file, data=data, context=self.get_context(), partial=True)

        self.assertTrue(serializer.is_valid())
        file = serializer.save()
        self.assertEqual(file.file_name, "updated_name.txt")

    def test_move_file_to_new_folder(self):
        new_folder = FolderFactory(name="new", user=self.user)
        data = {"folder": new_folder.id}
        serializer = self.serializer(instance=self.file, data=data, context=self.get_context(), partial=True)

        self.assertTrue(serializer.is_valid())
        file = serializer.save()
        self.assertEqual(file.folder, new_folder)

    def test_rename_and_move_file(self):
        new_folder = FolderFactory(name="nested", user=self.user)
        data = {"file_name": "combo", "folder": new_folder.id}
        serializer = self.serializer(instance=self.file, data=data, context=self.get_context(), partial=True)

        self.assertTrue(serializer.is_valid())
        file = serializer.save()
        self.assertEqual(file.file_name, "combo.txt")
        self.assertEqual(file.folder, new_folder)

    def test_empty_payload_does_not_change_file(self):
        data = {}
        serializer = self.serializer(instance=self.file, data=data, context=self.get_context(), partial=True)

        self.assertTrue(serializer.is_valid())
        file = serializer.save()
        self.assertEqual(file.file_name, "document.txt")
        self.assertEqual(file.folder, self.folder)

    def test_file_name_with_slash_invalid(self):
        data = {"file_name": "bad/name"}
        serializer = self.serializer(instance=self.file, data=data, context=self.get_context(), partial=True)

        with self.assertRaises(ValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn("file_name", cm.exception.detail)

    def test_file_name_with_backslash_invalid(self):
        data = {"file_name": "bad\\name"}
        serializer = self.serializer(
            instance=self.file,
            data=data,
            context=self.get_context(),
            partial=True
        )

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_file_name_with_dot_prefix_suffix_invalid(self):
        for name in [".hidden", "trailing."]:
            serializer = self.serializer(
                instance=self.file,
                data={"file_name": name},
                context=self.get_context(),
                partial=True
            )

            with self.assertRaises(ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_file_name_with_whitespace_only_invalid(self):
        data = {"file_name": "   "}
        serializer = self.serializer(
            instance=self.file,
            data=data,
            context=self.get_context(),
            partial=True
        )

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    @patch.object(CloudFile, "rebuild_path")
    def test_rebuild_path_is_called(self, mock_rebuild):
        data = {"file_name": "renamed"}
        serializer = self.serializer(
            instance=self.file,
            data=data,
            context=self.get_context(),
            partial=True
        )
        serializer.is_valid()
        serializer.save()

        self.assertTrue(mock_rebuild.called)
