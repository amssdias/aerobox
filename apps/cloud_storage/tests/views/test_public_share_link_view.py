from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.factories.share_link_factory import ShareLinkFactory
from apps.users.factories.user_factory import UserFactory


class PublicShareLinkDetailTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="andre",
            email="andre@example.com",
            password="dummy-pass",
        )

        cls.base_expires_at = timezone.now() + timezone.timedelta(days=1)

    def _create_share_link(self, **kwargs):
        defaults = {
            "owner": self.user,
            "expires_at": self.base_expires_at,
        }
        defaults.update(kwargs)
        return ShareLinkFactory(**defaults)

    def test_returns_meta_for_password_protected_link(self):
        share_link = self._create_share_link(password="some-password")

        url = reverse("public-share-link-detail", kwargs={"token": share_link.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["token"], share_link.token)
        self.assertEqual(data["owner_name"], self.user.get_full_name())
        self.assertTrue(data["is_password_protected"])

        self.assertNotIn("files", data)
        self.assertNotIn("folders", data)

    def test_returns_full_details_for_non_password_link(self):
        share_link = self._create_share_link(password=None, token="public-token")

        file1 = CloudFileFactory(user=self.user)
        file2 = CloudFileFactory(user=self.user)
        folder1 = FolderFactory(user=self.user)
        folder2 = FolderFactory(user=self.user)

        share_link.files.set([file1, file2])
        share_link.folders.set([folder1, folder2])

        url = reverse("public-share-link-detail", kwargs={"token": share_link.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["token"], share_link.token)
        self.assertFalse(data["is_password_protected"])

        self.assertIn("files", data)
        self.assertIn("folders", data)
        self.assertEqual(len(data["files"]), 2)
        self.assertEqual(len(data["folders"]), 2)

    def test_returns_404_for_nonexistent_token(self):
        url = reverse("public-share-link-detail", kwargs={"token": "does-not-exist"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "The link you’re trying to open doesn’t exist.",
        )

    def test_returns_410_for_revoked_link(self):
        share_link = self._create_share_link(revoked_at=timezone.now())

        url = reverse("public-share-link-detail", kwargs={"token": share_link.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            response.data["detail"],
            "This link has been disabled by the owner.",
        )

    def test_returns_410_for_expired_link(self):
        expired_at = timezone.now() - timezone.timedelta(days=1)
        share_link = self._create_share_link(
            expires_at=expired_at,
        )

        url = reverse("public-share-link-detail", kwargs={"token": share_link.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            response.data["detail"],
            "This link has expired and can’t be accessed anymore.",
        )


class PublicShareLinkUnlockTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="andre",
            email="andre@example.com",
            password="dummy-pass",
        )
        cls.base_expires_at = timezone.now() + timezone.timedelta(days=1)

    def _create_share_link(self, **kwargs):
        defaults = {
            "owner": self.user,
            "password": None,
            "expires_at": self.base_expires_at,
        }
        defaults.update(kwargs)
        return ShareLinkFactory(**defaults)

    def test_get_on_unlock_endpoint_is_not_allowed(self):
        share_link = self._create_share_link(token="get-not-allowed")
        share_link.set_password("secret123")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unlock_non_password_protected_link_returns_400(self):
        share_link = self._create_share_link(password=None)

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "anything"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "This link is not password protected.",
        )

    def test_unlock_with_invalid_password_returns_400(self):
        share_link = self._create_share_link()

        share_link.set_password("correct-password")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "wrong-password"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid password.")

    def test_unlock_with_valid_password_returns_full_details(self):
        share_link = self._create_share_link(token="valid-pass-token")
        share_link.set_password("secret123")
        share_link.save(update_fields=["password"])

        file1 = CloudFileFactory(user=self.user)
        folder1 = FolderFactory(user=self.user)
        share_link.files.add(file1)
        share_link.folders.add(folder1)

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "secret123"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn("files", data)
        self.assertIn("folders", data)
        self.assertEqual(len(data["files"]), 1)
        self.assertEqual(len(data["folders"]), 1)

    def test_unlock_nonexistent_token_returns_404(self):
        url = reverse("public-share-unlock", kwargs={"token": "does-not-exist"})
        response = self.client.post(url, {"password": "anything"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "The link you’re trying to open doesn’t exist.",
        )

    def test_unlock_revoked_link_returns_410(self):
        share_link = self._create_share_link(revoked_at=timezone.now())
        share_link.set_password("secret")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "secret"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            response.data["detail"],
            "This link has been disabled by the owner.",
        )

    def test_unlock_expired_link_returns_410(self):
        expired_at = timezone.now() - timezone.timedelta(days=1)
        share_link = self._create_share_link(expires_at=expired_at)
        share_link.set_password("secret")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "secret"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            response.data["detail"],
            "This link has expired and can’t be accessed anymore.",
        )

    def test_unlock_with_missing_password_treated_as_invalid(self):
        share_link = self._create_share_link(token="missing-pass-token")
        share_link.set_password("secret123")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})

        # No password field at all
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid password.")

    def test_unlock_with_empty_password_string_returns_invalid(self):
        share_link = self._create_share_link(token="empty-pass-token")
        share_link.set_password("secret123")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid password.")

    def test_successful_unlock_never_exposes_password_field(self):
        share_link = self._create_share_link(token="no-password-leak")
        share_link.set_password("secret123")
        share_link.save(update_fields=["password"])

        url = reverse("public-share-unlock", kwargs={"token": share_link.token})
        response = self.client.post(url, {"password": "secret123"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertNotIn("password", data)
        self.assertIn("token", data)
        self.assertIn("files", data)
        self.assertIn("folders", data)
