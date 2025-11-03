from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class UserUpdateUsernameTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("users:user")
        cls.user = UserFactory(username="test", email="test@example.com")
        cls.other = UserFactory(username="taken", email="taken@example.com")

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_patch_requires_auth(self):
        self.client.logout()
        resp = self.client.patch(self.url, {"username": "newname"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_username_success(self):
        resp = self.client.patch(self.url, {"username": "newname"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newname")

    def test_update_username_must_be_unique(self):
        resp = self.client.patch(self.url, {"username": self.other.username}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", resp.data)

    def test_cannot_update_other_fields(self):
        email = self.user.email
        resp = self.client.patch(self.url, {"username": "onlyname", "email": "hacker@evil.com"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "onlyname")
        self.assertEqual(self.user.email, email)
