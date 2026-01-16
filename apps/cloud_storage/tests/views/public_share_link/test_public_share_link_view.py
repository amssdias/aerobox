from unittest.mock import patch

from django.core.signing import SignatureExpired
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.cloud_storage.tests.factories.share_link_factory import ShareLinkFactory
from apps.cloud_storage.views.mixins.share_link import ShareLinkAccessMixin
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
        cls.access_mixin = ShareLinkAccessMixin()

    def _access_header(self, token: str):
        """
        Helper to build the header dict for the DRF test client.
        'X-ShareLink-Access' -> HTTP_X_SHARELINK_ACCESS in tests.
        """
        return {"HTTP_X_SHARELINK_ACCESS": token}

    def _create_share_link(self, **kwargs):
        defaults = {
            "owner": self.user,
            "expires_at": self.base_expires_at,
        }
        defaults.update(kwargs)
        return ShareLinkFactory(**defaults)

    def test_public_share_link_without_password_returns_200_without_token(self):
        share_link = self._create_share_link()
        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_share_link_without_password_ignores_access_token_header(self):
        share_link = self._create_share_link()
        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )
        fake_token = "whatever"
        response = self.client.get(url, **self._access_header(fake_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_share_link_with_password_and_valid_token_returns_200(self):
        share_link = self._create_share_link(password="some-password")
        access_token = self.access_mixin.build_access_token(share_link)

        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )

        response = self.client.get(
            url,
            **self._access_header(access_token),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], share_link.token)
        self.assertEqual(response.data["owner_name"], self.user.get_full_name())
        self.assertTrue(response.data["is_password_protected"])
        self.assertIn("files", response.data)
        self.assertIn("folders", response.data)

    def test_public_share_link_with_password_missing_token_returns_401(self):
        share_link = self._create_share_link(password="some-password")

        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_share_link_with_password_invalid_token_returns_401(self):
        invalid_token = "totally-invalid-token-string"
        share_link = self._create_share_link(password="some-password")

        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )

        response = self.client.get(
            url,
            **self._access_header(invalid_token),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_share_link_with_password_token_for_other_share_link_returns_401(self):
        share_link = self._create_share_link(password="some-password")
        other_share_link = self._create_share_link(password="some-other-password")
        other_token = self.access_mixin.build_access_token(other_share_link)

        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )

        # Try to use other_token on self.share_link_with_pw
        response = self.client.get(
            url,
            **self._access_header(other_token),
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_share_link_with_password_expired_token_returns_401(self):
        share_link = self._create_share_link(password="some-password")
        access_token = self.access_mixin.build_access_token(share_link)
        url = reverse(
            "public-share-link-detail",
            kwargs={"token": share_link.token},
        )

        with patch(
                "apps.cloud_storage.views.mixins.share_link.ShareLinkAccessMixin.signer.unsign",
                side_effect=SignatureExpired("Token expired"),
        ):
            response = self.client.get(
                url,
                **self._access_header(access_token),
            )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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


class PublicShareLinkAuthViewTests(APITestCase):
    def setUp(self):
        self.owner = UserFactory(username="test")

        # Share link that REQUIRES password
        self.protected_link = ShareLinkFactory(owner=self.owner)
        self.protected_link.set_password("correct-password")
        self.protected_link.save()

        # Share link WITHOUT password
        self.unprotected_link = ShareLinkFactory(owner=self.owner)

    def get_url(self, token):
        return reverse("public-share-link-auth", kwargs={"token": token})

    def test_valid_password_returns_access_token(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "correct-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIsNotNone(response.data["access_token"])
        self.assertIn("expires_in", response.data)
        self.assertIn("token_type", response.data)
        self.assertEqual(response.data["token_type"], "sharelink_access")

    def test_invalid_password_returns_401(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertIn("Invalid password", str(response.data["detail"]))

    def test_missing_password_field_returns_401(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_password_treated_as_invalid(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_link_without_password_returns_requires_password_false(self):
        response = self.client.post(
            self.get_url(self.unprotected_link.token),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("requires_password", response.data)
        self.assertFalse(response.data["requires_password"])
        self.assertIn("access_token", response.data)
        self.assertIsNone(response.data["access_token"])
        self.assertIsNone(response.data["expires_in"])

    def test_link_without_password_ignores_password_field(self):
        response = self.client.post(
            self.get_url(self.unprotected_link.token),
            {"password": "whatever"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["requires_password"])
        self.assertIsNone(response.data["access_token"])

    def test_invalid_token_returns_404(self):
        response = self.client.post(
            self.get_url("non-existent-token"),
            {"password": "anything"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_build_access_token_called_with_share_link(self):
        with patch.object(
                ShareLinkAccessMixin,
                "build_access_token",
                return_value="dummy-token",
        ) as mocked_build:
            response = self.client.post(
                self.get_url(self.protected_link.token),
                {"password": "correct-password"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_build.assert_called_once()
        called_arg = mocked_build.call_args[0][0]
        self.assertEqual(called_arg.pk, self.protected_link.pk)
        self.assertEqual(response.data["access_token"], "dummy-token")

    def test_expires_in_uses_access_max_age(self):
        with patch.object(ShareLinkAccessMixin, "access_max_age", 999):
            response = self.client.post(
                self.get_url(self.protected_link.token),
                {"password": "correct-password"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["expires_in"], 999)

    def test_anonymous_user_can_authenticate_share_link(self):
        self.client.logout()
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "correct-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_requires_password_not_in_protected_success_response(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "correct-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("requires_password", response.data)

    def test_get_method_not_allowed(self):
        response = self.client.get(self.get_url(self.protected_link.token))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_access_token_is_string_on_success(self):
        with patch.object(
                ShareLinkAccessMixin,
                "build_access_token",
                return_value="string-token-123",
        ):
            response = self.client.post(
                self.get_url(self.protected_link.token),
                {"password": "correct-password"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["access_token"], str)

    def test_extra_fields_in_payload_are_ignored(self):
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "correct-password", "foo": "bar"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_form_encoded_body_still_works(self):
        # no format="json" -> uses application/x-www-form-urlencoded
        response = self.client.post(
            self.get_url(self.protected_link.token),
            {"password": "correct-password"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
