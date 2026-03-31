from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from apps.integrations.stripe.payments.dto.checkout_session import CheckoutSessionInfo
from apps.payments.domain.exceptions import CheckoutSessionPermissionDeniedError
from apps.payments.services.stripe_api import get_stripe_session_info


class GetStripeSessionInfoTests(SimpleTestCase):
    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_return_checkout_session_summary_when_customer_belongs_to_user(self, mock_get_stripe_session):
        user = SimpleNamespace(
            profile=SimpleNamespace(stripe_customer_id="cus_123")
        )
        session = {
            "id": "cs_123",
            "status": "complete",
            "mode": "subscription",
            "payment_status": "paid",
            "amount_total": 1299,
            "currency": "eur",
            "created": 1774962092,
            "customer": {
                "id": "cus_123",
                "email": "user@example.com",
            },
        }
        mock_get_stripe_session.return_value = session
        result = get_stripe_session_info("cs_123", user)

        mock_get_stripe_session.assert_called_once_with("cs_123")
        self.assertIsInstance(result, CheckoutSessionInfo)
        self.assertEqual(result.id, session.get("id"))
        self.assertEqual(result.status, session.get("status"))
        self.assertEqual(result.mode, session.get("mode"))
        self.assertEqual(result.payment_status, session.get("payment_status"))
        self.assertEqual(result.amount_total, session.get("amount_total"))
        self.assertEqual(result.currency, session.get("currency"))
        self.assertEqual(result.created, session.get("created"))
        self.assertEqual(result.customer_email, session.get("customer").get("email"))
        self.assertEqual(result.payment_status, session.get("payment_status"))

    @patch("apps.payments.services.stripe_api.to_checkout_session_summary")
    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_raise_permission_denied_when_user_has_no_stripe_customer_id(
            self,
            mock_get_stripe_session,
            mock_to_checkout_session_summary,
    ):
        user = SimpleNamespace(
            profile=SimpleNamespace(stripe_customer_id=None)
        )
        session = {
            "id": "cs_123",
            "customer": {
                "id": "cus_123",
            },
        }

        mock_get_stripe_session.return_value = session

        with self.assertRaisesMessage(
                CheckoutSessionPermissionDeniedError,
                _("Unable to validate checkout session ownership."),
        ):
            get_stripe_session_info("cs_123", user)

        mock_get_stripe_session.assert_called_once_with("cs_123")
        mock_to_checkout_session_summary.assert_not_called()

    @patch("apps.payments.services.stripe_api.to_checkout_session_summary")
    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_raise_permission_denied_when_session_customer_id_is_missing(
            self,
            mock_get_stripe_session,
            mock_to_checkout_session_summary,
    ):
        user = SimpleNamespace(
            profile=SimpleNamespace(stripe_customer_id="cus_123")
        )
        session = {
            "id": "cs_123",
            "customer": None,
        }

        mock_get_stripe_session.return_value = session

        with self.assertRaisesMessage(
                CheckoutSessionPermissionDeniedError,
                _("Unable to validate checkout session ownership."),
        ):
            get_stripe_session_info("cs_123", user)

        mock_get_stripe_session.assert_called_once_with("cs_123")
        mock_to_checkout_session_summary.assert_not_called()

    @patch("apps.payments.services.stripe_api.to_checkout_session_summary")
    @patch("apps.payments.services.stripe_api.get_stripe_session")
    def test_should_raise_permission_denied_when_customer_does_not_belong_to_user(
            self,
            mock_get_stripe_session,
            mock_to_checkout_session_summary,
    ):
        user = SimpleNamespace(
            profile=SimpleNamespace(stripe_customer_id="cus_user")
        )
        session = {
            "id": "cs_123",
            "customer": {
                "id": "cus_other",
            },
        }

        mock_get_stripe_session.return_value = session

        with self.assertRaisesMessage(
                CheckoutSessionPermissionDeniedError,
                _("You do not have permission to access this checkout session."),
        ):
            get_stripe_session_info("cs_123", user)

        mock_get_stripe_session.assert_called_once_with("cs_123")
        mock_to_checkout_session_summary.assert_not_called()
