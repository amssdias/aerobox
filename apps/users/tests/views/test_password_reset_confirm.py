from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CustomPasswordResetConfirmViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(email="user@example.com")
        cls.user.set_password("OldPassword123")
        cls.user.save()
        cls.uid = urlsafe_base64_encode(force_bytes(cls.user.pk))
        cls.token = default_token_generator.make_token(cls.user)
        cls.url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": cls.uid, "token": cls.token},
        )

    def test_password_reset_successful(self):
        response = self.client.post(
            self.url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Password has been reset.", response.data["message"])

    def test_password_reset_confirm_get_not_allowed(self):
        response = self.client.get(self.url, kwargs={"uidb64": "test-uid", "token": "test-token"})
        self.assertEqual(response.status_code, 405)

    def test_password_reset_passwords_do_not_match(self):
        response = self.client.post(
            self.url,
            data={
                "new_password1": "NewPassword123",
                "new_password2": "DifferentPassword456",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Passwords do not match.", response.data["non_field_errors"])

    def test_password_reset_missing_passwords(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password1", response.data)
        self.assertIn("new_password2", response.data)

    def test_password_reset_empty_passwords(self):
        response = self.client.post(
            self.url, data={"new_password1": "", "new_password2": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_invalid_token(self):
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": self.uid, "token": "invalidtoken"},
        )
        response = self.client.post(
            url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid token.", response.data["error"])

    def test_password_reset_invalid_uid(self):
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": "invaliduid", "token": self.token},
        )
        response = self.client.post(
            url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid user or token.", response.data["error"])

    def test_password_reset_expired_token(self):
        self.user.set_password("OldPassword123")
        self.user.save()
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": self.uid, "token": "expiredtoken"},
        )
        response = self.client.post(
            url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid token.", response.data["error"])

    def test_password_reset_user_does_not_exist(self):
        non_existent_uid = urlsafe_base64_encode(force_bytes(99999))
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": non_existent_uid, "token": self.token},
        )
        response = self.client.post(
            url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid user or token.", response.data["error"])

    def test_password_reset_weak_password(self):
        response = self.client.post(
            self.url, data={"new_password1": "123", "new_password2": "123"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password1", response.data)

    def test_password_reset_only_one_password_provided(self):
        response = self.client.post(self.url, data={"new_password1": "NewPassword123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password2", response.data)

    def test_password_reset_successful_and_password_is_updated(self):
        response = self.client.post(
            self.url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123"))

    def test_password_reset_case_insensitive_token(self):
        token_lower = self.token.lower()
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": self.uid, "token": token_lower},
        )
        response = self.client.post(
            url,
            data={"new_password1": "NewPassword123", "new_password2": "NewPassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Password has been reset.", response.data["message"])
