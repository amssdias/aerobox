from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.models import ShareLink
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.cloud_storage.tests.factories.share_link_factory import ShareLinkFactory
from apps.cloud_storage.views.mixins.share_link import ShareLinkAccessMixin


class PublicShareLinkFileDownloadViewTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.folder = FolderFactory(
            name="Test folder",
        )

        cls.file = CloudFileFactory(
            file_name="test.txt",
            folder=cls.folder,
        )

        cls.other_file = CloudFileFactory(
            file_name="other.txt",
            folder=cls.folder,
        )

        cls.share_link = ShareLinkFactory(
            files=[cls.file]
        )

        # Share link with password
        cls.protected_share_link = ShareLinkFactory(
            files=[cls.file]
        )
        cls.password = "secret-password"
        cls.protected_share_link.set_password(cls.password)
        cls.protected_share_link.save()

        cls.url_name = "public-share-file-download"
        cls.access_mixin = ShareLinkAccessMixin()

    def get_url(self, token, file_id):
        return reverse(self.url_name, kwargs={"token": token, "file_id": file_id})

    @patch.object(S3Service, "generate_presigned_download_url")
    def test_download_without_password_success(self, mock_s3_service):
        mock_s3_service.return_value = "https://s3/url"

        url = self.get_url(self.share_link.token, self.file.id)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "https://s3/url")
        mock_s3_service.assert_called_once_with(
            object_name=self.file.s3_key
        )

    @patch.object(S3Service, "generate_presigned_download_url")
    def test_download_with_correct_password_success(self, mock_s3_service):
        mock_s3_service.return_value = "https://s3/url"

        url = self.get_url(self.protected_share_link.token, self.file.id)
        access_token = self.access_mixin.build_access_token(self.protected_share_link)

        response = self.client.post(
            url,
            data={},
            HTTP_X_SHARELINK_ACCESS=access_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "https://s3/url")

    def test_download_missing_password_returns_400(self):
        url = self.get_url(self.protected_share_link.token, self.file.id)
        response = self.client.post(url, data={})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_download_invalid_password_returns_400(self):
        url = self.get_url(self.protected_share_link.token, self.file.id)
        response = self.client.post(
            url,
            data={},
            HTTP_X_SHARELINK_ACCESS="wrong-token"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_download_nonexistent_file_returns_404(self):
        non_existent_id = self.file.id + 9999
        url = self.get_url(self.share_link.token, non_existent_id)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_file_not_belonging_to_share_link_returns_404(self):
        url = self.get_url(self.share_link.token, self.other_file.id)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_download_revoked_share_link_returns_400(self):
        self.share_link.revoked_at = timezone.now()
        self.share_link.save(update_fields=["revoked_at"])
        url = self.get_url(self.share_link.token, self.file.id)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    def test_download_expired_share_link_returns_400(self):
        self.share_link.expires_at = timezone.now() - timedelta(days=1)
        self.share_link.save(update_fields=["expires_at"])
        url = self.get_url(self.share_link.token, self.file.id)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    @patch.object(S3Service, "generate_presigned_download_url")
    def test_anonymous_user_can_access_endpoint(self, mock_s3_service):
        mock_s3_service.return_value = "https://s3/url"

        url = self.get_url(self.share_link.token, self.file.id)
        self.client.logout()
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch.object(S3Service, "generate_presigned_download_url")
    def test_s3_service_not_called_when_cannot_access_file(self, mock_s3_service):
        with patch.object(
                ShareLink, "can_access_file", return_value=False
        ) as mock_can_access:
            url = self.get_url(self.share_link.token, self.file.id)
            response = self.client.post(url, data={})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_can_access.assert_called_once()
        mock_s3_service.assert_not_called()

    @patch.object(S3Service, "generate_presigned_download_url")
    def test_s3_service_error_results_in_400(self, mock_s3_service):
        mock_s3_service.side_effect = RuntimeError("S3 error")

        url = self.get_url(self.share_link.token, self.file.id)
        response = self.client.post(url, data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
