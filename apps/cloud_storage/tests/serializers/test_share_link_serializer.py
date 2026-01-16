from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.cloud_storage.models import ShareLink, CloudFile, Folder
from apps.cloud_storage.serializers.share_link_serializer import ShareLinkSerializer
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.cloud_storage.tests.factories.share_link_factory import ShareLinkFactory
from apps.users.factories.user_factory import UserFactory


class ShareLinkSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="test-user")
        cls.serializer = ShareLinkSerializer

        cls.file = CloudFileFactory(file_name="test.txt")
        cls.folder = FolderFactory(name="My Folder")

    def _get_context(self):
        return {"request": SimpleNamespace(user=self.user)}

    # Helper to inject file_sharing_config
    def _patch_file_sharing_config(self, config):
        patcher = patch.object(
            type(self.user),
            "file_sharing_config",
            new_callable=PropertyMock,
        )
        mock_prop = patcher.start()
        self.addCleanup(patcher.stop)
        mock_prop.return_value = config
        return mock_prop

    def test_validate_requires_files_or_folders(self):
        data = {
            "files": [],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())

        self.assertFalse(serializer.is_valid())
        self.assertIn("A share link must include at least one file or folder.", str(serializer.errors))

    def test_validate_with_files_only_is_valid(self):
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid())

    def test_validate_with_folders_only_is_valid(self):
        data = {
            "files": [],
            "folders": [self.folder.id],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_to_representation_includes_files_with_id_and_name(self):
        sharelink = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(minutes=60),
        )
        sharelink.files.add(self.file)

        serializer = ShareLinkSerializer(instance=sharelink)
        data = serializer.data

        self.assertIn("files", data)
        self.assertEqual(len(data["files"]), 1)
        self.assertEqual(data["files"][0]["id"], self.file.id)
        self.assertEqual(data["files"][0]["name"], self.file.file_name)

    def test_create_sets_owner_to_request_user(self):
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()

        self.assertEqual(sharelink.owner, self.user)

        day_after = timezone.now() + timedelta(minutes=1440)
        self.assertEqual(sharelink.expires_at.day, day_after.day)
        self.assertIsNone(sharelink.password)

    def test_create_hashes_password_when_provided(self):
        raw_password = "Secret123!"
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": raw_password,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()

        self.assertNotEqual(sharelink.password, raw_password)

    def test_create_leaves_password_none_when_not_provided(self):
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()

        self.assertIsNone(sharelink.password)

    def test_create_hashes_password(self):
        new_password = "new-password"
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": new_password,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()

        self.assertTrue(sharelink.password)
        self.assertTrue(sharelink.check_password(new_password))
        self.assertNotEqual(sharelink.password, new_password)

    def test_create_sets_default_expiration_when_not_allowed_to_choose(self):
        max_minutes = 90
        self._patch_file_sharing_config({
            "allow_choose_expiration": False,
            "max_expiration_minutes": max_minutes,
        })

        before = timezone.now()
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()
        after = timezone.now()

        expected_min = before + timedelta(minutes=max_minutes)
        expected_max = after + timedelta(minutes=max_minutes)

        self.assertGreaterEqual(sharelink.expires_at, expected_min)
        self.assertLessEqual(sharelink.expires_at, expected_max)

    def test_create_respects_expires_at_when_allowed_to_choose(self):
        max_minutes = 120
        self._patch_file_sharing_config({
            "allow_choose_expiration": True,
            "max_expiration_minutes": max_minutes,
        })

        custom_expiration = timezone.now() + timedelta(minutes=30)

        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": custom_expiration,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()

        # Should not override since it's within allowed range
        self.assertEqual(sharelink.expires_at, custom_expiration)

    def test_create_overrides_expires_at_when_not_allowed_to_choose(self):
        max_minutes = 60
        self._patch_file_sharing_config({
            "allow_choose_expiration": False,
            "max_expiration_minutes": max_minutes,
        })

        far_future = timezone.now() + timedelta(days=10)

        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": far_future,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        before = timezone.now()
        sharelink = serializer.save()
        after = timezone.now()

        expected_min = before + timedelta(minutes=max_minutes)
        expected_max = after + timedelta(minutes=max_minutes)

        self.assertGreaterEqual(sharelink.expires_at, expected_min)
        self.assertLessEqual(sharelink.expires_at, expected_max)

    def test_create_uses_default_expiration_when_config_has_no_max(self):
        default_minutes = getattr(settings, "DEFAULT_SHARELINK_EXPIRATION_MINUTES", 1440)
        self._patch_file_sharing_config({
            "allow_choose_expiration": False,
            # intentionally omitting "max_expiration_minutes"
        })

        before = timezone.now()
        data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save()
        after = timezone.now()

        expected_min = before + timedelta(minutes=default_minutes)
        expected_max = after + timedelta(minutes=default_minutes)

        self.assertGreaterEqual(sharelink.expires_at, expected_min)
        self.assertLessEqual(sharelink.expires_at, expected_max)

    def test_read_only_fields_cannot_be_set_by_client(self):
        base_data = {
            "files": [self.file.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(data=base_data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        sharelink = serializer.save()

        data = {
            "id": 9999,
            "files": [self.file.id],
            "token": "1234",
            "folders": [],
            "expires_at": None,
            "password": None,
        }
        serializer = ShareLinkSerializer(instance=sharelink, data=data, context=self._get_context(), partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.id, sharelink.id)
        self.assertNotEqual(sharelink.token, "1234")

    def test_create_share_link_saves_files_only(self):
        data = {
            "files": [self.file.pk],
            "folders": [],
            "expires_at": None,
            "password": None,
        }

        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save(owner=self.user)

        sharelink.refresh_from_db()
        self.assertEqual(ShareLink.objects.count(), 1)

        self.assertQuerysetEqual(
            sharelink.files.order_by("pk"),
            CloudFile.objects.filter(pk=self.file.pk).order_by("pk"),
            transform=lambda x: x,
        )
        self.assertEqual(sharelink.folders.count(), 0)

    def test_create_share_link_saves_folders_only(self):
        data = {
            "files": [],
            "folders": [self.folder.pk],
            "expires_at": None,
            "password": None,
        }

        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save(owner=self.user)

        sharelink.refresh_from_db()
        self.assertEqual(ShareLink.objects.count(), 1)

        self.assertQuerysetEqual(
            sharelink.folders.order_by("pk"),
            Folder.objects.filter(pk=self.folder.pk).order_by("pk"),
            transform=lambda x: x,
        )
        self.assertEqual(sharelink.files.count(), 0)

    def test_create_share_link_saves_files_and_folders(self):
        data = {
            "files": [self.file.pk],
            "folders": [self.folder.pk],
            "expires_at": None,
            "password": None,
        }

        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        sharelink = serializer.save(owner=self.user)

        sharelink.refresh_from_db()
        self.assertEqual(ShareLink.objects.count(), 1)

        self.assertQuerysetEqual(
            sharelink.files.all(),
            CloudFile.objects.filter(pk=self.file.pk),
            transform=lambda x: x,
        )
        self.assertQuerysetEqual(
            sharelink.folders.all(),
            Folder.objects.filter(pk=self.folder.pk),
            transform=lambda x: x,
        )

    def test_create_share_link_with_deleted_file(self):
        file = CloudFileFactory(deleted_at=timezone.now())
        data = {
            "files": [file.pk],
            "folders": [self.folder.pk],
            "expires_at": None,
            "password": None,
        }

        serializer = ShareLinkSerializer(data=data, context=self._get_context())
        self.assertFalse(serializer.is_valid())
