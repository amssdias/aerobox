from django.test import TestCase
from django.utils import timezone

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.factories.share_link_factory import ShareLinkFactory
from apps.cloud_storage.serializers import CloudFilesSerializer, FolderDetailSerializer
from apps.cloud_storage.serializers.public_share_serializer import (
    PublicShareLinkMetaSerializer,
    PublicShareLinkDetailSerializer,
)
from apps.users.factories.user_factory import UserFactory


class PublicShareLinkMetaSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="test",
            first_name="Testing",
            last_name="Surname",
        )

        cls.user_only_username = UserFactory(
            username="no-name",
            first_name="",
            last_name="",
        )
        cls.share_link_base_kwargs = {
            "token": "27rJu-OG-KqE6FLErxGxYQ",
            "expires_at": timezone.now() + timezone.timedelta(days=1),
            "created_at": timezone.now(),
        }

    def test_owner_name_uses_get_full_name_when_available(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            password=None,
            **self.share_link_base_kwargs,
        )

        serializer = PublicShareLinkMetaSerializer(share_link)
        data = serializer.data

        self.assertEqual(data["owner_name"], self.user.get_full_name())

    def test_owner_name_falls_back_to_username_when_full_name_blank(self):
        share_link = ShareLinkFactory(
            owner=self.user_only_username,
            password=None,
            **self.share_link_base_kwargs,
        )

        serializer = PublicShareLinkMetaSerializer(share_link)
        data = serializer.data

        self.assertEqual(data["owner_name"], self.user_only_username.username)

    def test_is_password_protected_true_when_password_present(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            password="some-hash-or-plain",
            **self.share_link_base_kwargs,
        )

        serializer = PublicShareLinkMetaSerializer(share_link)
        data = serializer.data

        self.assertTrue(data["is_password_protected"])

    def test_is_password_protected_false_when_password_blank_or_none(self):
        share_link_none = ShareLinkFactory(
            owner=self.user,
            password=None,
            **self.share_link_base_kwargs,
        )
        share_link_blank = ShareLinkFactory(
            owner=self.user,
            password="",
            token="another-token",
            expires_at=self.share_link_base_kwargs["expires_at"],
            created_at=self.share_link_base_kwargs["created_at"],
        )

        serializer_none = PublicShareLinkMetaSerializer(share_link_none)
        serializer_blank = PublicShareLinkMetaSerializer(share_link_blank)

        self.assertFalse(serializer_none.data["is_password_protected"])
        self.assertFalse(serializer_blank.data["is_password_protected"])

    def test_meta_serializer_fields_and_read_only(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            password=None,
            **self.share_link_base_kwargs,
        )

        serializer = PublicShareLinkMetaSerializer(share_link)

        expected_fields = (
            "token",
            "owner_name",
            "expires_at",
            "created_at",
            "is_password_protected",
        )

        self.assertEqual(tuple(serializer.fields.keys()), expected_fields)

        for field_name in expected_fields:
            self.assertTrue(
                serializer.fields[field_name].read_only,
                msg=f"Field {field_name} should be read_only",
            )


class PublicShareLinkDetailSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="andre",
            first_name="André",
            last_name="Dias",
            password="dummy",
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

    def test_detail_serializer_fields_extend_meta_fields(self):
        serializer = PublicShareLinkDetailSerializer(self.share_link)

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

    def test_detail_serializer_files_and_folders_are_read_only(self):
        serializer = PublicShareLinkDetailSerializer(self.share_link)

        self.assertTrue(serializer.fields["files"].read_only)
        self.assertTrue(serializer.fields["folders"].read_only)

    def test_detail_serializer_uses_correct_nested_serializers(self):
        serializer = PublicShareLinkDetailSerializer(self.share_link)

        files_field = serializer.fields["files"]
        folders_field = serializer.fields["folders"]

        self.assertEqual(files_field.child.__class__, CloudFilesSerializer)
        self.assertEqual(folders_field.child.__class__, FolderDetailSerializer)

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
