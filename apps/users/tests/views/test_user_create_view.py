from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class UserCreateViewTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("users:user")
        cls.valid_user_data = {
            "username": "testuser",
            "email": "testing@test.com",
            "password": "strongpassword123",
            "password2": "strongpassword123",
        }

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_create_user_successfully(self, mock_create_customer):
        response = self.client.post(self.url, self.valid_user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("username", response.data)
        self.assertEqual(response.data["username"], self.valid_user_data["username"])
        self.assertEqual(response.data["email"], self.valid_user_data["email"])
        self.assertTrue(
            User.objects.filter(username=self.valid_user_data["username"]).exists()
        )

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_create_profile_successfully(self, mock_create_customer):
        response = self.client.post(self.url, self.valid_user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("username", response.data)
        self.assertEqual(response.data["username"], self.valid_user_data["username"])
        self.assertEqual(response.data["email"], self.valid_user_data["email"])
        user = User.objects.get(username=self.valid_user_data["username"])
        self.assertTrue(user.profile)
        self.assertTrue(user.profile.stripe_customer_id)
        mock_create_customer.assert_called_once()

    def test_user_create_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_create_user_with_missing_data(self):
        incomplete_data = {"username": "incompleteuser"}
        response = self.client.post(self.url, incomplete_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertIn("email", response.data)
        self.assertFalse(User.objects.filter(username="incompleteuser").exists())

    def test_create_user_with_duplicate_username(self):
        user = {
            "username": "duplicated-user",
            "email": "duplicated-user@test.com",
            "password": "strongPassword123",
            "password2": "strongPassword123",
        }
        UserFactory(username=user.get("username"))
        response = self.client.post(self.url, user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_create_user_with_duplicate_email(self):
        user = {
            "username": "duplicated-user",
            "email": "duplicated-user@test.com",
            "password": "strongPassword123",
            "password2": "strongPassword123",
        }
        UserFactory(email=user.get("email"))
        response = self.client.post(self.url, user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "email", response.data
        )  # Assuming the serializer will return an "email" error

    def test_create_user_with_no_data(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)
        self.assertIn("email", response.data)

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_create_user_with_extra_fields(self, mock_create_customer):
        extra_data = {
            "username": "extrafielduser",
            "password": "extrafieldpassword123",
            "password2": "extrafieldpassword123",
            "email": "extrafielduser@example.com",
            "not_a_field": "this_field_is_not_in_the_serializer",
        }
        response = self.client.post(self.url, extra_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("username", response.data)
        self.assertNotIn("not_a_field", response.data)  # Should not be in the response
        self.assertTrue(User.objects.filter(username="extrafielduser").exists())

    def test_create_user_with_long_username(self):
        long_username_data = {
            "username": "a" * 151,
            "password": "somepassword123",
            "password2": "somepassword123",
            "email": "longusernameuser@example.com",
        }
        response = self.client.post(self.url, long_username_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
