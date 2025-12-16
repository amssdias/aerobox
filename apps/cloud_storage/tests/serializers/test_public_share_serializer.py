from django.test import TestCase
from django.utils import timezone

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.factories.share_link_factory import ShareLinkFactory
from apps.cloud_storage.serializers import CloudFilesSerializer, FolderParentSerializer
from apps.cloud_storage.serializers.public_share_serializer import (
    PublicShareLinkDetailSerializer,
    PublicShareFolderDetailSerializer,
)
from apps.users.factories.user_factory import UserFactory


class PublicShareLinkDetailSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="andre",
            first_name="André",
            last_name="Dias",
            password="dummy",
        )
        cls.user_only_username = UserFactory(
            username="no-name",
            first_name="",
            last_name="",
        )

        cls.file1 = CloudFileFactory(
            file_name="file1.txt",
            user=cls.user,
        )
        cls.file2 = CloudFileFactory(
            file_name="file2.jpg",
            user=cls.user,
        )

        cls.folder1 = FolderFactory(
            name="Folder 1",
            user=cls.user,
        )
        cls.folder2 = FolderFactory(
            name="Folder 2",
            user=cls.user,
        )

        cls.share_link = ShareLinkFactory(
            owner=cls.user,
            token="27rJu-OG-KqE6FLErxGxYQ",
            password=None,
            expires_at=timezone.now() + timezone.timedelta(days=1),
            created_at=timezone.now(),
            files=[cls.file1, cls.file2],
            folders=[cls.folder1, cls.folder2],
        )

    def test_owner_name_uses_get_full_name_when_available(self):
        share_link = ShareLinkFactory(owner=self.user)

        serializer = PublicShareLinkDetailSerializer(share_link)
        data = serializer.data

        self.assertEqual(data["owner_name"], self.user.get_full_name())

    def test_owner_name_falls_back_to_username_when_full_name_blank(self):
        share_link = ShareLinkFactory(owner=self.user_only_username)

        serializer = PublicShareLinkDetailSerializer(share_link)
        data = serializer.data

        self.assertEqual(data["owner_name"], self.user_only_username.username)

    def test_is_password_protected_true_when_password_present(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            password="some-password",
        )

        serializer = PublicShareLinkDetailSerializer(share_link)
        data = serializer.data

        self.assertTrue(data["is_password_protected"])

    def test_is_password_protected_false_when_password_blank_or_none(self):
        share_link_none = ShareLinkFactory(
            owner=self.user,
        )
        share_link_blank = ShareLinkFactory(
            owner=self.user,
            password="",
        )

        serializer_none = PublicShareLinkDetailSerializer(share_link_none)
        serializer_blank = PublicShareLinkDetailSerializer(share_link_blank)

        self.assertFalse(serializer_none.data["is_password_protected"])
        self.assertFalse(serializer_blank.data["is_password_protected"])

    def test_meta_serializer_fields_and_read_only(self):
        share_link = ShareLinkFactory(owner=self.user)

        serializer = PublicShareLinkDetailSerializer(share_link)

        expected_fields = (
            "token",
            "owner_name",
            "expires_at",
            "created_at",
            "is_password_protected",
            "files",
            "folders",
        )

        self.assertEqual(tuple(serializer.fields.keys()), expected_fields)

        for field_name in expected_fields:
            self.assertTrue(
                serializer.fields[field_name].read_only,
                msg=f"Field {field_name} should be read_only",
            )

    def test_detail_serializer_uses_correct_nested_serializers(self):
        serializer = PublicShareLinkDetailSerializer(self.share_link)

        files_field = serializer.fields["files"]
        folders_field = serializer.fields["folders"]

        self.assertEqual(files_field.child.__class__, CloudFilesSerializer)
        self.assertEqual(folders_field.child.__class__, FolderParentSerializer)

    def test_detail_serializer_includes_serialized_files_and_folders(self):
        serializer = PublicShareLinkDetailSerializer(
            self.share_link, context={"user": self.user}
        )
        data = serializer.data

        self.assertIn("files", data)
        self.assertIn("folders", data)

        self.assertEqual(len(data["files"]), 2)
        self.assertEqual(len(data["folders"]), 2)

        file_names = {f["file_name"] for f in data["files"]}
        folder_names = {f["name"] for f in data["folders"]}

        self.assertSetEqual(file_names, {"file1.txt", "file2.jpg"})
        self.assertSetEqual(folder_names, {"Folder 1", "Folder 2"})


class TestPublicShareFolderDetailSerializer(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.root_folder = FolderFactory(name="root")

        cls.folder = FolderFactory(name="main", parent=cls.root_folder)

        # Subfolders under main
        cls.subfolder_1 = FolderFactory(name="sub_1", parent=cls.folder)
        cls.subfolder_2 = FolderFactory(name="sub_2", parent=cls.folder)

        cls.file_1 = CloudFileFactory(
            file_name="file_1", folder=cls.folder, user=cls.user
        )
        cls.file_2 = CloudFileFactory(
            file_name="file_2", folder=cls.folder, user=cls.user
        )

        cls.serializer = PublicShareFolderDetailSerializer

    def test_serializer_includes_expected_top_level_fields(self):
        data = self.serializer(self.folder).data
        self.assertEqual(
            set(data.keys()), {"id", "name", "parent", "subfolders", "files"}
        )

    def test_serializer_id_and_name_match_instance(self):
        data = self.serializer(self.folder).data
        self.assertEqual(data["id"], self.folder.id)
        self.assertEqual(data["name"], self.folder.name)

    def test_parent_is_serialized_when_present(self):
        data = self.serializer(self.folder).data
        self.assertIsNotNone(data["parent"])

    def test_parent_is_none_when_no_parent(self):
        data = self.serializer(self.root_folder).data
        self.assertIsNone(data["parent"])

    def test_subfolders_is_a_list(self):
        data = self.serializer(self.folder).data
        self.assertIsInstance(data["subfolders"], list)

    def test_files_is_a_list(self):
        data = self.serializer(self.folder).data
        self.assertIsInstance(data["files"], list)

    def test_subfolders_returns_correct_count(self):
        data = self.serializer(self.folder).data
        self.assertEqual(len(data["subfolders"]), 2)

    def test_files_returns_correct_count(self):
        data = self.serializer(self.folder).data
        self.assertEqual(len(data["files"]), 2)

    def test_subfolders_empty_when_no_subfolders(self):
        empty_folder = FolderFactory(
            name="empty_no_subfolders", parent=self.root_folder
        )
        data = self.serializer(empty_folder).data
        self.assertEqual(data["subfolders"], [])

    def test_files_empty_when_no_files(self):
        empty_folder = FolderFactory(name="empty_no_files", parent=self.root_folder)
        data = self.serializer(empty_folder).data
        self.assertEqual(data["files"], [])

    def test_get_subfolders_uses_simplefolderserializer_with_many_true(self):
        serializer = self.serializer(self.root_folder)
        subfolders = serializer.get_subfolders(self.root_folder)

        self.assertEqual(subfolders[0]["id"], self.folder.id)
        self.assertEqual(subfolders[0]["name"], self.folder.name)
        self.assertEqual(subfolders[0]["subfolders_count"], 2)
        self.assertEqual(subfolders[0]["files_count"], 2)

    def test_get_files_uses_cloudfilesserializer_with_many_true(self):
        new_file = CloudFileFactory(
            file_name="file_1_1", folder=self.root_folder, user=self.user
        )
        serializer = self.serializer(self.root_folder)
        files = serializer.get_files(self.root_folder)

        self.assertEqual(files[0]["id"], new_file.id)
        self.assertEqual(files[0]["file_name"], new_file.file_name)
        self.assertEqual(files[0]["size"], new_file.size)
        self.assertEqual(files[0]["content_type"], new_file.content_type)
