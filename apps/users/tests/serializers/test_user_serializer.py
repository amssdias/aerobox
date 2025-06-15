from unittest.mock import patch, Mock

from django.test import TestCase

from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.users.factories.user_factory import UserFactory
from apps.users.serializers import UserSerializer


class UserSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        PlanFactory(name={"en": "Free"}, is_free=True)
        cls.serializer = UserSerializer

    def setUp(self):
        self.data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_serializer_valid_data_creates_user(self, mock_create_customer):
        serializer = self.serializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()
        self.assertEqual(user.username, self.data["username"])
        self.assertEqual(user.email, self.data["email"])

        # Verify password is hashed
        self.assertTrue(user.check_password(self.data["password"]))

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_serializer_valid_data_creates_profile(self, mock_create_customer):
        serializer = self.serializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()
        self.assertTrue(user.profile)

    @patch("stripe.Customer.create", return_value=Mock(id="cus_mocked_123456"))
    def test_serializer_valid_data_creates_stripe_customer(self, mock_create_customer):
        serializer = self.serializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()
        self.assertTrue(user.profile.stripe_customer_id)
        mock_create_customer.assert_called_once()

    def test_serializer_password_mismatch(self):
        self.data["password2"] = "1234"
        serializer = self.serializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password2", serializer.errors)
        self.assertEqual(
            serializer.errors["password2"][0], "The two password fields must match."
        )

    def test_serializer_missing_fields(self):
        invalid_data = {"username": "testuser"}
        serializer = self.serializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("password", serializer.errors)
        self.assertIn("password2", serializer.errors)

    def test_serializer_duplicate_user(self):
        UserFactory(
            username="testuser",
            email="testuser@example.com",
            password="StrongPassword123!",
        )
        serializer = UserSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_valid_email_creates_user(self):
        serializer = UserSerializer(data=self.data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_duplicate_email_raises_error(self):
        UserFactory(email=self.data.get("email"))
        serializer = UserSerializer(data=self.data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertEqual(
            serializer.errors["email"][0],
            "A user with this email already exists. Please use a different email address."
        )

    def test_empty_email_raises_error(self):
        self.data["email"] = ""
        serializer = UserSerializer(data=self.data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_missing_email_field_raises_error(self):
        del self.data["email"]
        serializer = UserSerializer(data=self.data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)