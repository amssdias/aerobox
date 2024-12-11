from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class UserLoginViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("users:user-login")
        cls.password = "StrongPassword1234"
        cls.user = UserFactory(username="username", email="user@example.com")
        cls.user.set_password(cls.password)
        cls.user.save()

    def test_user_login_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_user_login_successfully(self):
        response = self.client.post(
            self.url, data={"username": self.user.username, "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIsInstance(response.data.get("token"), str)

    def test_user_login_no_body_sent(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)

    def test_user_login_email_only(self):
        response = self.client.post(self.url, data={"username": self.user.username})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertNotIn("username", response.data)

    def test_user_login_password_only(self):
        response = self.client.post(self.url, data={"password": self.password})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertNotIn("password", response.data)

    def test_user_login_wrong_password(self):
        response = self.client.post(
            self.url,
            data={"username": self.user.username, "password": "WrongPassword1234"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertNotIn("username", response.data)
        self.assertNotIn("password", response.data)

    def test_user_login_with_non_existent_email(self):
        response = self.client.post(
            self.url,
            data={"username": "nonexistentusername", "password": self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_with_created_user_email_and_different_user_password(self):
        other_user = UserFactory(username="otheruser", email="otheruser@example.com")
        other_user.set_password("AnotherPassword123")
        other_user.save()

        response = self.client.post(
            self.url,
            data={"username": self.user.username, "password": "AnotherPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_empty_email_and_password(self):
        response = self.client.post(self.url, data={"username": "", "password": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)

    def test_user_login_empty_email_and_valid_password(self):
        response = self.client.post(
            self.url, data={"username": "", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_valid_email_and_empty_password(self):
        response = self.client.post(
            self.url, data={"username": self.user.email, "password": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertNotIn("username", response.data)

    def test_user_login_with_whitespace_email_and_password(self):
        response = self.client.post(
            self.url, data={"username": "   ", "password": "   "}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertNotIn("password", response.data)

    def test_user_login_case_insensitive_email(self):
        response = self.client.post(
            self.url,
            data={"username": self.user.username.upper(), "password": self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
