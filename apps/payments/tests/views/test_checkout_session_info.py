from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.test import APITestCase

from apps.integrations.stripe.payments.exceptions import (
    StripeCheckoutSessionError,
    StripeCheckoutSessionNotFoundError,
)
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class CheckoutSessionInfoViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="test")
        cls.stripe_customer_id = "cus_123"
        cls.user.profile.stripe_customer_id = cls.stripe_customer_id
        cls.user.profile.save()

        cls.url = reverse("payments:checkout-get-session-info")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_checkout_session_info_success(
            self,
            mock_get_stripe_session,
    ):
        stripe_session = {
            "id": "cs_test_123",
            "status": "complete",
            "payment_status": "paid",
            "mode": "subscription",
            "customer": {
                "id": self.stripe_customer_id,
                "email": "user@example.com",
            },
            "amount_total": 999,
            "currency": "eur",
            "created": 1711468800,
        }

        mock_get_stripe_session.return_value = stripe_session

        response = self.client.get(self.url, {"session_id": "cs_test_123"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), stripe_session.get("id"))
        self.assertEqual(response.data.get("status"), stripe_session.get("status"))
        self.assertEqual(response.data.get("payment_status"), stripe_session.get("payment_status"))
        self.assertEqual(response.data.get("mode"), stripe_session.get("mode"))
        self.assertEqual(response.data.get("amount_total"), stripe_session.get("amount_total"))
        self.assertEqual(response.data.get("currency"), stripe_session.get("currency"))
        self.assertEqual(response.data.get("customer_email"), stripe_session.get("customer").get("email"))
        self.assertEqual(response.data.get("created"), stripe_session.get("created"))
        mock_get_stripe_session.assert_called_once_with("cs_test_123")

    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_403_when_checkout_session_does_not_belong_to_user(
            self,
            mock_get_stripe_session,
    ):
        mock_get_stripe_session.return_value = {
            "id": "cs_test_789",
            "customer": {
                "id": "cus_other",
                "email": "other@example.com",
            },
        }

        response = self.client.get(self.url, {"session_id": "cs_test_789"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {
                "detail": str(
                    _("You do not have permission to access this checkout session.")
                )
            },
        )
        mock_get_stripe_session.assert_called_once_with("cs_test_789")

    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_403_when_checkout_session_ownership_cannot_be_validated(
            self,
            mock_get_stripe_session,
    ):
        user = UserFactory(username="test-2")
        user.profile.stripe_customer_id = None
        user.profile.save()

        mock_get_stripe_session.return_value = {
            "id": "cs_test_999",
            "customer": {
                "id": "cus_123",
                "email": "user@example.com",
            },
        }
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url, {"session_id": "cs_test_999"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {
                "detail": str(_("Unable to validate checkout session ownership."))
            },
        )
        mock_get_stripe_session.assert_called_once_with("cs_test_999")

    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_404_when_stripe_checkout_session_is_not_found(
            self,
            mock_get_stripe_session,
    ):
        mock_get_stripe_session.side_effect = StripeCheckoutSessionNotFoundError(
            "Checkout session not found."
        )

        response = self.client.get(self.url, {"session_id": "cs_missing"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data,
            {"detail": "Checkout session not found."},
        )
        mock_get_stripe_session.assert_called_once_with("cs_missing")

    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_502_when_stripe_returns_generic_error(
            self,
            mock_get_stripe_session,
    ):
        mock_get_stripe_session.side_effect = StripeCheckoutSessionError(
            "Stripe error while retrieving checkout session."
        )

        response = self.client.get(self.url, {"session_id": "cs_error"})

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            response.data,
            {"detail": "Stripe error while retrieving checkout session."},
        )
        mock_get_stripe_session.assert_called_once_with("cs_error")

    def test_should_return_400_when_session_id_is_missing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("session_id", response.data)

    def _test_should_return_400_when_session_id_is_invalid(self):
        response = self.client.get(self.url, {"session_id": "e_error"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("session_id", response.data)
