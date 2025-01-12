import logging
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from django.urls import reverse

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.path_utils import build_s3_path
from apps.users.factories.user_factory import UserFactory


class CloudStorageRetrieveTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser1")
        cls.token, _ = Token.objects.get_or_create(user=cls.user)

        # Create a file object for the user
        path = build_s3_path(
            user_id=cls.user.id,
            file_name="docs",
        )
        cls.file = CloudFileFactory(user=cls.user, path=path)
        cls.url = reverse("storage-detail", kwargs={"pk": cls.file.id})

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("apps.cloud_storage.services.S3Service.generate_presigned_download_url")
    def test_retrieve_existing_file_with_valid_url(self, mock_generate_url):
        mock_generate_url.return_value = "https://s3.amazonaws.com/bucket/test_file.txt"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertEqual(response.data["url"], "https://s3.amazonaws.com/bucket/test_file.txt")

    @patch.object(S3Service,"generate_presigned_download_url",return_value=None)
    def test_retrieve_existing_file_with_missing_url(self, mock_generate_url):
        """Test retrieving a file when S3 fails to generate a presigned URL."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            str(response.data["detail"]),
            "Unable to generate download URL. The file may not exist or there was an error with the storage service."
        )

    @patch("apps.cloud_storage.services.s3_service.logger", return_value=logging.getLogger("null"))
    def test_retrieve_non_existent_file(self, mock_logger):
        """Test retrieving a non-existent file should return 404."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_without_authentication(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_file_of_other_user(self):
        other_user = UserFactory(username="otheruser")

        # Create a file object for the user
        path = build_s3_path(
            user_id=other_user.id,
            file_name="docs",
        )
        other_file = CloudFileFactory(user=other_user, path=path)
        url = reverse("storage-detail", kwargs={"pk": other_file.id})
        response = self.client.get(url)

        # Retrieves a 404 because the logged user don´t have that file ID associated to him
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
