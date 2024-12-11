from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings

from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CustomPasswordResetViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("users:password_reset")
        cls.user_email = "user@example.com"
        cls.user = UserFactory(email=cls.user_email)
        cls.user.set_password("SecurePassword123")
        cls.user.save()

    def test_password_reset_successful(self):
        response = self.client.post(self.url, data={"email": self.user_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Password reset link sent.", response.data["message"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user_email, mail.outbox[0].to)

    def test_password_reset_url_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_password_reset_missing_email(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email is required.", response.data["error"])

    def test_password_reset_email_not_registered(self):
        response = self.client.post(self.url, data={"email": "nonexistent@example.com"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("User with this email does not exist.", response.data["error"])

    def test_password_reset_invalid_email_format(self):
        response = self.client.post(self.url, data={"email": "invalid-email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Invalid email format.", response.data["error"]
        )

    def test_password_reset_empty_email(self):
        response = self.client.post(self.url, data={"email": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email is required.", response.data["error"])

    def test_password_reset_whitespace_email(self):
        response = self.client.post(self.url, data={"email": "   "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email is required.", response.data["error"])

    def test_password_reset_email_case_insensitive(self):
        response = self.client.post(self.url, data={"email": self.user_email.upper()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user_email, mail.outbox[0].to)

    def test_password_reset_email_sends_correct_content(self):
        response = self.client.post(self.url, data={"email": self.user_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email=self.user_email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        self.assertIn(uid, mail.outbox[0].body)
        self.assertIn(token, mail.outbox[0].body)

    def test_password_reset_no_duplicate_emails_sent(self):
        for _ in range(3):
            response = self.client.post(self.url, data={"email": self.user_email})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(mail.outbox), 3)

    def test_password_reset_rate_limiting(self):
        for _ in range(10):
            response = self.client.post(self.url, data={"email": self.user_email})

        self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
