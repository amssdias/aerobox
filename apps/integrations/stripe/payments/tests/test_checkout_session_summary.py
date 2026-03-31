from django.test import SimpleTestCase

from apps.integrations.stripe.payments.dto.checkout_session import CheckoutSessionInfo
from apps.integrations.stripe.payments.mappers.checkout_session import (
    to_checkout_session_summary,
)


class ToCheckoutSessionSummaryTests(SimpleTestCase):
    def test_should_map_checkout_session_when_customer_is_expanded_dict(self):
        session = {
            "id": "cs_test_123",
            "status": "complete",
            "payment_status": "paid",
            "mode": "subscription",
            "customer": {
                "id": "cus_123",
                "email": "user@example.com",
            },
            "amount_total": 999,
            "currency": "eur",
            "created": 1711468800,
        }

        result = to_checkout_session_summary(session)

        self.assertIsInstance(result, CheckoutSessionInfo)
        self.assertEqual(result.id, "cs_test_123")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.payment_status, "paid")
        self.assertEqual(result.mode, "subscription")
        self.assertEqual(result.customer_email, "user@example.com")
        self.assertEqual(result.amount_total, 999)
        self.assertEqual(result.currency, "eur")
        self.assertEqual(result.created, 1711468800)

    def test_should_use_customer_details_email_when_customer_is_not_dict(self):
        session = {
            "id": "cs_test_456",
            "status": "open",
            "payment_status": "unpaid",
            "mode": "payment",
            "customer": "cus_456",
            "customer_details": {
                "email": "fallback@example.com",
            },
            "amount_total": 2500,
            "currency": "usd",
            "created": 1711469999,
        }

        result = to_checkout_session_summary(session)

        self.assertEqual(result.id, "cs_test_456")
        self.assertEqual(result.status, "open")
        self.assertEqual(result.payment_status, "unpaid")
        self.assertEqual(result.mode, "payment")
        self.assertEqual(result.customer_email, "fallback@example.com")
        self.assertEqual(result.amount_total, 2500)
        self.assertEqual(result.currency, "usd")
        self.assertEqual(result.created, 1711469999)

    def test_should_return_none_for_customer_email_when_customer_and_customer_details_have_no_email(self):
        session = {
            "id": "cs_test_789",
            "status": "complete",
            "payment_status": "paid",
            "mode": "subscription",
            "customer": "cus_789",
            "customer_details": {},
            "amount_total": 5000,
            "currency": "gbp",
            "created": 1711471111,
        }

        result = to_checkout_session_summary(session)

        self.assertEqual(result.customer_email, None)
        self.assertEqual(result.amount_total, 5000)
        self.assertEqual(result.currency, "gbp")
        self.assertEqual(result.created, 1711471111)

    def test_should_return_none_for_optional_fields_when_missing(self):
        session = {
            "id": "cs_test_minimal",
            "customer": "cus_minimal",
        }

        result = to_checkout_session_summary(session)

        self.assertEqual(result.id, "cs_test_minimal")
        self.assertIsNone(result.status)
        self.assertIsNone(result.payment_status)
        self.assertIsNone(result.mode)
        self.assertIsNone(result.customer_email)
        self.assertIsNone(result.amount_total)
        self.assertIsNone(result.currency)
        self.assertIsNone(result.created)
