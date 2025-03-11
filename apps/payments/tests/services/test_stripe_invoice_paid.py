from unittest.mock import patch

from django.test import TestCase

from datetime import datetime, timezone
from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.stripe_events.invoice_paid import InvoicePaidHandler


class InvoicePaidHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.payment = PaymentFactory(
            amount=15.00,
        )

    def setUp(self):
        self.timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        self.data = {
            "data": {
                "object": {
                    "id": self.payment.stripe_invoice_id,
                    "customer": self.payment.user.profile.stripe_customer_id,
                    "subscription": self.payment.subscription.stripe_subscription_id,
                    "status_transitions": {"paid_at": self.timestamp},
                    "payment_intent": "pi_123",
                    "amount_paid": 1500,
                    "status": "paid",
                }
            }
        }
        self.handler = InvoicePaidHandler(self.data)

    def test_get_invoice_id_success(self):
        self.assertEqual(self.handler.get_invoice_id(), self.payment.stripe_invoice_id)

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.critical")
    def test_get_invoice_id_missing(self, mock_logger):
        del self.handler.data["id"]
        with self.assertRaises(ValueError) as context:
            self.handler.get_invoice_id()

        mock_logger.asser_called_once()

    def test_get_payment_from_db_success(self):
        retrieved_payment = self.handler.get_payment(self.payment.stripe_invoice_id)

        self.assertEqual(retrieved_payment, self.payment)

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    def test_get_payment_not_found(self, mock_logger):
        retrieved_payment = self.handler.get_payment("nonexistent_id")

        self.assertIsNone(retrieved_payment)
        mock_logger.asser_called_once()

    def test_extract_payment_date_success(self):
        expected_datetime = datetime.utcfromtimestamp(self.timestamp).replace(
            tzinfo=timezone.utc
        )

        self.assertEqual(self.handler.extract_payment_date(), expected_datetime)

    def test_extract_payment_date_missing(self):
        del self.handler.data["status_transitions"]

        result = self.handler.extract_payment_date()
        self.assertIsNone(result)

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_method")
    def test_get_payment_method_success(
        self, mock_get_payment_method, mock_get_payment_intent
    ):
        mock_get_payment_intent.return_value = {"payment_method": "pm_123"}
        mock_get_payment_method.return_value = {"type": "card"}

        result = self.handler.get_payment_method()

        self.assertEqual(result, "card")
        mock_get_payment_intent.assert_called_once_with("pi_123")
        mock_get_payment_method.assert_called_once_with("pm_123")

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_missing_payment_intent_id(
        self, mock_get_payment_intent, mock_logger
    ):
        self.handler.data["payment_intent"] = ""

        result = self.handler.get_payment_method()

        self.assertIsNone(result)
        mock_get_payment_intent.assert_not_called()
        mock_logger.asser_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_payment_intent_not_found(
        self, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = ""

        result = self.handler.get_payment_method()

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once()
        mock_logger.asser_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_missing_payment_method(
        self, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = {"payment_method": ""}

        result = self.handler.get_payment_method()

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once_with("pi_123")
        mock_logger.asser_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_method")
    def test_get_payment_method_payment_method_not_found(
        self, mock_get_payment_method, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = {"payment_method": "pm_123"}
        mock_get_payment_method.return_value = ""

        result = self.handler.get_payment_method()

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once_with("pi_123")
        mock_get_payment_method.assert_called_once_with("pm_123")
        mock_logger.asser_called_once()

    def test_extract_amount_paid_success(self):
        result = self.handler.extract_amount_paid()

        self.assertEqual(result, 15.00)

    def test_extract_amount_paid_missing(self):
        del self.handler.data["amount_paid"]

        result = self.handler.extract_amount_paid()
        self.assertIsNone(result)

    def test_get_status_success(self):
        result = self.handler.get_invoice_status()
        self.assertEqual(result, "paid")

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    def test_get_status_missing_key(self, mock_logger):
        del self.handler.data["status"]
        result = self.handler.get_invoice_status()

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_can_update_success(self):
        result = self.handler.can_update(
            invoice_id=self.payment.stripe_invoice_id,
            payment=self.payment,
            payment_method="card",
            amount=self.payment.amount,
            payment_date=datetime.now(timezone.utc),
            status="paid",
        )

        self.assertTrue(result)

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_missing_payment(self, mock_logger):

        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=None,
                payment_method="card",
                amount=10.00,
                payment_date=datetime.now(timezone.utc),
                invoice_id=self.payment.stripe_invoice_id,
                status="paid",
            )

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_missing_payment_method(self, mock_logger):

        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=self.payment,
                payment_method=None,
                amount=10.00,
                payment_date=datetime.now(timezone.utc),
                invoice_id=self.payment.stripe_invoice_id,
                status="paid",
            )

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_missing_amount(self, mock_logger):

        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=self.payment,
                payment_method="card",
                amount=None,
                payment_date=datetime.now(timezone.utc),
                invoice_id=self.payment.stripe_invoice_id,
                status="paid",
            )

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_missing_payment_date(self, mock_logger):

        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=self.payment,
                payment_method="card",
                amount=10.00,
                payment_date=None,
                invoice_id=self.payment.stripe_invoice_id,
                status="paid",
            )

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_amount_distinct(self, mock_logger):
        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=self.payment,
                payment_method="card",
                amount=self.payment.amount + 2,
                payment_date=datetime.now(timezone.utc),
                invoice_id=self.payment.stripe_invoice_id,
                status="paid",
            )

        mock_logger.assert_called_once()

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_success(self, mock_get_payment_method):
        mock_get_payment_method.return_value = "card"

        self.handler.process()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, "card")
        self.assertEqual(str(self.payment.amount), "15.00")
        expected_datetime = datetime.utcfromtimestamp(self.timestamp).replace(
            tzinfo=timezone.utc
        )
        self.assertEqual(self.payment.payment_date, expected_datetime)

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_missing_payment(self, mock_get_payment_method):
        mock_get_payment_method.return_value = "card"
        self.handler.data["id"] = "in_5423345"

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_missing_payment_method(self, mock_get_payment_method):
        mock_get_payment_method.return_value = None

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_amount_wrong_type(self, mock_get_payment_method):
        mock_get_payment_method.return_value = "card"
        self.handler.data["amount_paid"] = None

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_payment_date_wrong_type(self, mock_get_payment_method):
        mock_get_payment_method.return_value = "card"
        self.handler.data["status_transitions"]["paid_at"] = None

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()
