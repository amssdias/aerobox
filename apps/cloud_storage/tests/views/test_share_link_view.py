from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.domain.exceptions.share_link import (
    FolderSharingNotAllowed,
    ShareLinkLimitReached,
    ShareLinkExpirationTooLong,
    ShareLinkPasswordNotAllowed,
)
from apps.cloud_storage.models import ShareLink
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.cloud_storage.tests.factories.share_link_factory import ShareLinkFactory
from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class ShareLinkViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="test-user-1")
        cls.other_user = UserFactory(username="test-user-2")

        # Create files for the authenticated user
        cls.file_1 = CloudFileFactory(user=cls.user)
        cls.file_2 = CloudFileFactory(user=cls.user)
        cls.deleted_file = CloudFileFactory(user=cls.user, deleted_at=timezone.now())

        cls.folder_1 = FolderFactory(name="Root", user=cls.user)
        cls.folder_2 = FolderFactory(name="Root", user=cls.user)

        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
        cls.feature = cls.subscription.plan.plan_features.get(
            feature__code=FeatureCodeChoices.FILE_SHARING
        )
        cls.feature.feature.metadata = {}
        cls.feature.feature.save(update_fields=["metadata"])

        cls.share_links_url = reverse("share-links-list")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def _attach_plan(self, file_sharing_config):
        self.feature.metadata = file_sharing_config
        self.feature.save(update_fields=["metadata"])

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.share_links_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_user_own_sharelinks_in_desc_order(self):
        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now() - timedelta(hours=10),
        )
        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now(),
        )
        ShareLinkFactory(
            owner=self.other_user,
            expires_at=None,
        )

        response = self.client.get(self.share_links_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 2)

    def test_list_returns_empty_list_when_user_has_no_sharelinks(self):
        response = self.client.get(self.share_links_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("results"), [])

    def test_retrieve_share_link_returns_correct_data(self):
        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now() - timedelta(hours=10),
        )
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now(),
        )
        ShareLinkFactory(
            owner=self.other_user,
            expires_at=None,
        )

        url = reverse("share-links-detail", args=[share_link.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("files", response.data)
        self.assertIn("folders", response.data)
        self.assertIn("id", response.data)
        self.assertIn("token", response.data)
        self.assertIn("password", response.data)
        self.assertIn("revoked_at", response.data)
        self.assertIn("expires_at", response.data)
        self.assertIn("created_at", response.data)
        self.assertEqual(response.data.get("id"), share_link.id)
        self.assertEqual(response.data.get("token"), share_link.token)
        self.assertIsNone(response.data.get("password"))
        self.assertIsNone(response.data.get("revoked_at"))

    def test_retrieve_requires_authentication(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now(),
        )
        self.client.logout()
        response = self.client.get(reverse("share-links-detail", args=[share_link.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_share_link_from_another_user(self):
        other_user_share_link = ShareLinkFactory(
            owner=self.other_user,
            expires_at=None,
        )

        url = reverse("share-links-detail", args=[other_user_share_link.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_share_link_expired(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=10),
        )

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("files", response.data)
        self.assertIn("folders", response.data)
        self.assertIn("id", response.data)
        self.assertIn("token", response.data)
        self.assertIn("password", response.data)
        self.assertIn("revoked_at", response.data)
        self.assertIn("expires_at", response.data)
        self.assertIn("created_at", response.data)
        self.assertEqual(response.data.get("id"), share_link.id)
        self.assertEqual(response.data.get("token"), share_link.token)
        self.assertIsNone(response.data.get("password"))
        self.assertIsNone(response.data.get("revoked_at"))

    def test_retrieve_share_link_revoked(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=12),
            created_at=timezone.now() - timedelta(hours=10),
            revoked_at=timezone.now(),
        )

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_share_link_success(self, mock_validate):
        mock_validate.return_value = True

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_validate.assert_called_once()

        # Sanity: one ShareLink created for this user
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 1)

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_share_link_ignores_revoked_at_in_payload(self, mock_validate):
        mock_validate.return_value = True

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            "password": None,
            "revoked_at": timezone.now().isoformat()
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_validate.assert_called_once()

        # Sanity: one ShareLink created for this user
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 1)

        share_link = ShareLink.objects.get(owner=self.user)
        self.assertIsNone(share_link.revoked_at)

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_folder_sharing_not_allowed_returns_403(self, mock_validate):
        mock_validate.side_effect = FolderSharingNotAllowed

        payload = {
            "files": [self.file_1.id],
            "folders": [1],
            "expires_at": None,
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "Your plan does not allow folder sharing. Upgrade to Pro to enable it.",
        )

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_share_link_limit_reached_returns_400_non_field_error(
            self, mock_validate
    ):
        mock_validate.side_effect = ShareLinkLimitReached

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn(
            "You have reached the maximum number of active share links for your plan.",
            response.data["non_field_errors"],
        )

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_expiration_too_long_returns_400_non_field_error(
            self, mock_validate
    ):
        mock_validate.side_effect = ShareLinkExpirationTooLong

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn(
            "Expiration exceeds the maximum allowed for your plan.",
            response.data["non_field_errors"],
        )

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_password_not_allowed_returns_403(self, mock_validate):
        mock_validate.side_effect = ShareLinkPasswordNotAllowed

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": None,
            "password": "secret123",
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "Your plan does not allow password-protected links.",
        )

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_invalid_serializer_does_not_call_validate(self, mock_validate):
        payload = {
            "folders": [],
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_validate.assert_not_called()

    @patch("apps.users.models.User.validate_create_or_update_sharelink")
    def test_create_with_multiple_files_links_them_to_sharelink(self, mock_validate):
        mock_validate.return_value = True

        second_file = CloudFileFactory()

        payload = {
            "files": [self.file_1.id, second_file.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(hours=2)).isoformat(),
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sharelink = ShareLink.objects.get(id=response.data["id"])
        linked_files = list(sharelink.files.order_by("id").values_list("id", flat=True))

        self.assertEqual(linked_files, sorted([self.file_1.id, second_file.id]))
        self.assertEqual(sharelink.owner, self.user)

    def test_create_share_link(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(minutes=30)).isoformat(),
            "password": "mypassword",
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 1)
        sharelink = ShareLink.objects.get(owner=self.user)
        self.assertIn(self.file_1, sharelink.files.all())

    def test_create_share_link_integration_hashes_password(self):
        self._attach_plan(
            {
                "allow_folder_sharing": False,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        new_password = "my-password"
        payload = {
            "files": [self.file_1.id],
            "expires_at": None,
            "password": new_password,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        share_link = ShareLink.objects.get(owner=self.user)
        self.assertTrue(share_link.check_password(new_password))
        self.assertNotEqual(share_link.password, new_password)

    def test_create_share_link_integration_folder_sharing_not_allowed(self):
        self._attach_plan(
            {
                "allow_folder_sharing": False,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        payload = {
            "files": [self.file_1.id],
            "folders": [self.folder_1.id],
            "expires_at": None,
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "Your plan does not allow folder sharing. Upgrade to Pro to enable it.",
        )
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 0)

    def test_cannot_create_share_link_with_non_root_folder(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        folder_3 = FolderFactory(parent=self.folder_1)

        payload = {
            "files": [self.file_1.id],
            "folders": [folder_3.id],
            "expires_at": None,
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_share_link_integration_max_active_links_reached(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 1,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
        )

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": None,
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn(
            "You have reached the maximum number of active share links for your plan.",
            response.data["non_field_errors"],
        )
        # Still only 1 link
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 1)

    def test_create_share_link_integration_expiration_too_long(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 30,
            }
        )

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(minutes=90)).isoformat(),
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn(
            "Expiration exceeds the maximum allowed for your plan.",
            response.data["non_field_errors"],
        )
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 0)

    def test_create_share_link_integration_password_not_allowed(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": False,  # no passwords allowed
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        payload = {
            "files": [self.file_1.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat(),
            "password": "secret123",
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "Your plan does not allow password-protected links.",
        )
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 0)

    def test_create_share_link_fails_for_deleted_file(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 60,
            }
        )

        payload = {
            "files": [self.deleted_file.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat(),
            "password": None,
        }

        response = self.client.post(self.share_links_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ShareLink.objects.filter(owner=self.user).count(), 0)
        self.assertIn("files", response.data)

    def test_delete_share_link(self):
        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now() - timedelta(hours=10),
        )
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now(),
        )
        ShareLinkFactory(
            owner=self.other_user,
            expires_at=None,
        )

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_requires_authentication(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=None,
            created_at=timezone.now(),
        )
        self.client.logout()
        response = self.client.delete(reverse("share-links-detail", args=[share_link.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_share_link_from_other_user(self):
        other_user_share_link = ShareLinkFactory(
            owner=self.other_user,
            expires_at=None,
        )

        url = reverse("share-links-detail", args=[other_user_share_link.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_share_link_expired(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=10),
        )

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_put_updates_files_for_active_share_link(self):
        expires_at = timezone.now() + timedelta(hours=24)
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=expires_at,
            created_at=timezone.now(),
        )

        new_expires = timezone.now() + timedelta(hours=5)

        payload = {
            "files": [self.file_2.id],
            "expires_at": new_expires.isoformat().replace("+00:00", "Z"),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()

        # Password changed
        self.assertIsNone(share_link.password)
        self.assertEqual(share_link.expires_at, expires_at)

        self.assertQuerysetEqual(
            share_link.files.order_by("id"),
            [self.file_2],
            transform=lambda x: x,
        )

    def test_put_can_change_only_password_keeping_files_and_folders(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 60,
            }
        )
        expires_at = timezone.now() + timedelta(hours=24)
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=expires_at,
            created_at=timezone.now(),
            files=[self.file_1],
            folders=[self.folder_1]
        )

        original_file_ids = list(share_link.files.values_list("id", flat=True))
        original_folder_ids = list(share_link.folders.values_list("id", flat=True))

        new_password = "another-new-password"
        payload = {
            "password": new_password,
            "expires_at": share_link.expires_at.isoformat().replace("+00:00", "Z"),
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()

        self.assertTrue(share_link.password)
        self.assertNotEqual(share_link.password, new_password)  # Hashed
        self.assertTrue(share_link.check_password(new_password))
        self.assertCountEqual(
            share_link.files.values_list("id", flat=True),
            original_file_ids,
        )
        self.assertCountEqual(
            share_link.folders.values_list("id", flat=True),
            original_folder_ids,
        )

    def test_put_can_change_only_files(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            created_at=timezone.now(),
            files=[self.file_1],
            folders=[self.folder_1]
        )

        payload = {
            "files": [self.file_2.id],
            "expires_at": share_link.expires_at.isoformat().replace("+00:00", "Z"),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertCountEqual(
            share_link.files.values_list("id", flat=True),
            [self.file_2.id],
        )

    def test_put_can_change_only_folders(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 60,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            created_at=timezone.now(),
            files=[self.file_1],
            folders=[self.folder_1]
        )

        payload = {
            "folders": [self.folder_2.id],
            "expires_at": share_link.expires_at.isoformat().replace("+00:00", "Z"),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertCountEqual(
            share_link.files.values_list("id", flat=True),
            [self.file_1.id],
        )
        self.assertCountEqual(
            share_link.folders.values_list("id", flat=True),
            [self.folder_2.id],
        )

    def test_put_can_remove_files_and_folders(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 600,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            created_at=timezone.now(),
            files=[self.file_1],
            folders=[self.folder_1]
        )

        payload = {
            "files": [],
            "folders": [],
            "expires_at": share_link.expires_at.isoformat().replace("+00:00", "Z"),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertCountEqual(
            share_link.files.values_list("id", flat=True),
            [],
        )
        self.assertCountEqual(
            share_link.folders.values_list("id", flat=True),
            [],
        )

    def test_put_can_change_expiration_time(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 180,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now(),
            files=[self.file_1],
        )

        new_expiration_time = timezone.now() + timedelta(hours=3)
        payload = {
            "expires_at": new_expiration_time.isoformat().replace("+00:00", "Z"),
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertEqual(share_link.expires_at.hour, new_expiration_time.hour)
        self.assertEqual(share_link.expires_at.minute, new_expiration_time.minute)
        self.assertEqual(share_link.expires_at.day, new_expiration_time.day)

    def test_put_can_change_expiration_time_exceed_limit(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 120,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now(),
            files=[self.file_1],
        )

        new_expiration_time = timezone.now() + timedelta(hours=4)
        payload = {
            "expires_at": new_expiration_time.isoformat().replace("+00:00", "Z"),
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_cannot_update_revoked_share_link(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            created_at=timezone.now(),
            files=[self.file_1],
            folders=[self.folder_1],
            revoked_at=timezone.now()
        )

        payload = {
            "files": [self.file_2.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat().replace(
                "+00:00", "Z"
            ),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_cannot_update_expired_share_link(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=25),
            files=[self.file_1],
        )

        payload = {
            "files": [self.file_2.id],
            "folders": [],
            "expires_at": (timezone.now() + timedelta(days=2)).isoformat().replace(
                "+00:00", "Z"
            ),
            "password": None,
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        share_link.refresh_from_db()
        self.assertCountEqual(
            share_link.files.values_list("id", flat=True),
            [self.file_1.id],
        )

    def test_put_cannot_update_folder(self):
        self._attach_plan(
            {
                "allow_folder_sharing": False,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 600,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        payload = {
            "folders": [self.folder_1.id],
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_cannot_update_password(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": False,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 600,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        payload = {
            "password": "new-password",
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_cannot_update_expiration(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": False,
                "allow_choose_expiration": False,
                "max_expiration_minutes": 600,
            }
        )

        expires_at = timezone.now() + timedelta(hours=1)
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        new_expiration_time = timezone.now() + timedelta(hours=4)
        payload = {
            "expires_at": new_expiration_time.isoformat().replace("+00:00", "Z"),
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        share_link.refresh_from_db()

        self.assertEqual(share_link.expires_at.month, expires_at.month)
        self.assertEqual(share_link.expires_at.day, expires_at.day)
        self.assertEqual(share_link.expires_at.hour, expires_at.hour)
        self.assertEqual(share_link.expires_at.minute, expires_at.minute)

        self.assertNotEqual(share_link.expires_at.hour, new_expiration_time.hour)

    def test_put_cannot_update_revoked_at(self):
        self._attach_plan(
            {
                "allow_folder_sharing": True,
                "max_active_links": 5,
                "allow_password": True,
                "allow_choose_expiration": True,
                "max_expiration_minutes": 600,
            }
        )

        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=3),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        payload = {
            "revoked_at": timezone.now().isoformat().replace("+00:00", "Z"),
        }

        url = reverse("share-links-detail", args=[share_link.id])
        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        share_link.refresh_from_db()

        self.assertIsNone(share_link.revoked_at)

    def test_revoke_active_share_link_success(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=3),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        url = reverse("share-links-revoke", args=[share_link.id])
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertIsNotNone(share_link.revoked_at)

        self.assertEqual(response.data["id"], share_link.id)
        self.assertIsNotNone(response.data.get("revoked_at"))

    def test_revoke_already_revoked_share_link_returns_400(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=3),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
            revoked_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse("share-links-revoke", args=[share_link.id])
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "This link is already revoked.")

        share_link.refresh_from_db()
        self.assertEqual(share_link.revoked_at, share_link.revoked_at)

    def test_cannot_revoke_share_link_of_another_user_returns_404(self):
        share_link = ShareLinkFactory(
            owner=self.other_user,
            expires_at=timezone.now() + timedelta(hours=3),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        url = reverse("share-links-revoke", args=[share_link.id])
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        share_link.refresh_from_db()
        self.assertIsNone(share_link.revoked_at)

    def test_revoke_share_link_requires_authentication(self):
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=timezone.now() + timedelta(hours=3),
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        self.client.logout()

        url = reverse("share-links-revoke", args=[share_link.id])
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        share_link.refresh_from_db()
        self.assertIsNone(share_link.revoked_at)

    def test_revoke_does_not_change_other_fields(self):
        expires_at = timezone.now() + timedelta(hours=3)
        share_link = ShareLinkFactory(
            owner=self.user,
            expires_at=expires_at,
            created_at=timezone.now() - timedelta(hours=20),
            files=[self.file_1],
        )

        url = reverse("share-links-revoke", args=[share_link.id])
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        share_link.refresh_from_db()
        self.assertIsNotNone(share_link.revoked_at)
        self.assertEqual(share_link.expires_at, expires_at)
        self.assertEqual(list(share_link.files.all()), [self.file_1])
