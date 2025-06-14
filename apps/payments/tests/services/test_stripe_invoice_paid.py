from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.constants.stripe_invoice import PAID
from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.stripe_events.invoice_paid import InvoicePaidHandler
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFactory


class InvoicePaidHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.payment = PaymentFactory(
            amount=15.00,
        )

    def setUp(self):
        # Patch stripe.Invoice.retrieve globally for this class
        patcher = patch("stripe.Invoice.retrieve")
        self.mock_retrieve_invoice = patcher.start()
        self.addCleanup(patcher.stop)  # Ensures patch is removed after each test

        self.timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        self.data = {
            "data": {
                "object": {
                    "id": self.payment.stripe_invoice_id,
                    "customer": self.payment.user.profile.stripe_customer_id,
                    "status_transitions": {"paid_at": self.timestamp},
                    "amount_paid": 1500,
                    "status": "paid",
                    "parent": {
                        "subscription_details": {
                            "subscription": self.payment.subscription.stripe_subscription_id
                        }
                    },
                    "payments": {
                        "data": [
                            {
                                "payment": {
                                    "payment_intent": "pi_123"
                                }
                            }
                        ]
                    }
                }
            }
        }

        self.stripe_invoice_mock = MagicMock(**self.data["data"]["object"])
        self.stripe_invoice_mock.parent = self.data["data"]["object"]["parent"]
        self.stripe_invoice_mock.payments = self.data["data"]["object"]["payments"]

        self.mock_retrieve_invoice.return_value = self.stripe_invoice_mock

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

    def test_get_invoice_paid_date_success(self):
        expected_datetime = datetime.utcfromtimestamp(self.timestamp).replace(
            tzinfo=timezone.utc
        )

        self.assertEqual(self.handler.get_invoice_paid_date(self.stripe_invoice_mock), expected_datetime)

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.warning")
    def test_get_invoice_paid_date_missing(self, mock_logger):
        self.stripe_invoice_mock.status_transitions = {"paid_at": None}

        result = self.handler.get_invoice_paid_date(self.stripe_invoice_mock)
        self.assertTrue(result)
        self.assertIsInstance(result, datetime)

        mock_logger.assert_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_method")
    def test_get_payment_method_success(
        self, mock_get_payment_method, mock_get_payment_intent
    ):
        mock_get_payment_intent.return_value = {"payment_method": "pm_123"}
        mock_get_payment_method.return_value = {"type": "card"}

        result = self.handler.get_payment_method(self.stripe_invoice_mock)

        self.assertEqual(result, "card")
        mock_get_payment_intent.assert_called_once_with("pi_123")
        mock_get_payment_method.assert_called_once_with("pm_123")

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_missing_payment_intent_id(
        self, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = None
        self.stripe_invoice_mock.payments = {
            "data": [
                {
                    "payment": {
                        "payment_intent": None
                    }
                }
            ]
        }

        result = self.handler.get_payment_method(self.stripe_invoice_mock)

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once()
        mock_logger.asser_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_payment_intent_not_found(
        self, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = ""

        result = self.handler.get_payment_method(self.stripe_invoice_mock)

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once()
        mock_logger.asser_called_once()

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.get_payment_intent")
    def test_get_payment_method_missing_payment_method(
        self, mock_get_payment_intent, mock_logger
    ):
        mock_get_payment_intent.return_value = {"payment_method": ""}

        result = self.handler.get_payment_method(self.stripe_invoice_mock)

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

        result = self.handler.get_payment_method(self.stripe_invoice_mock)

        self.assertIsNone(result)
        mock_get_payment_intent.assert_called_once_with("pi_123")
        mock_get_payment_method.assert_called_once_with("pm_123")
        mock_logger.asser_called_once()

    def test_valid_conversion(self):
        self.assertEqual(self.handler.convert_cents_to_euros(1500), 15.00)
        self.assertEqual(self.handler.convert_cents_to_euros(0), 0.0)

    def test_raises_value_error_on_none(self):
        with self.assertRaises(ValueError):
            self.handler.convert_cents_to_euros(None)

    def test_raises_value_error_on_negative(self):
        with self.assertRaises(ValueError):
            self.handler.convert_cents_to_euros(-1)

    def test_get_status_success(self):
        result = self.handler.get_invoice_status(PAID)
        self.assertEqual(result, PaymentStatusChoices.PAID)

    @patch("config.services.stripe_services.stripe_events.invoice_event_mixin.logger.error")
    def test_get_status_missing_key(self, mock_logger):
        result = self.handler.get_invoice_status(None)

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_can_update_success(self):
        result = self.handler.can_update(
            invoice_id=self.payment.stripe_invoice_id,
            payment=self.payment,
            payment_method="card",
            amount=self.payment.amount,
            status=PAID,
        )

        self.assertTrue(result)

    @patch("apps.payments.services.stripe_events.invoice_paid.logger.error")
    def test_can_update_missing_payment(self, mock_logger):

        with self.assertRaises(RuntimeError) as context:
            self.handler.can_update(
                payment=None,
                payment_method="card",
                amount=10.00,
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
        mock_get_payment_method.return_value = ""
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
        self.stripe_invoice_mock.amount_paid = None

        with self.assertRaises(ValueError) as context:
            self.handler.process()

    @patch(
        "apps.payments.services.stripe_events.invoice_paid.InvoicePaidHandler.get_payment_method"
    )
    def test_update_payment_success_email_sent(self, mock_get_payment_method):
        mock_get_payment_method.return_value = "card"

        self.handler.process()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.payment.user.email, mail.outbox[0].to)

    def test_updates_subscription_when_end_date_is_today(self):
        subscription = SubscriptionFactory(end_date=timezone.now().date())
        self.handler.update_subscription(subscription)
        subscription.refresh_from_db()

        self.assertEqual(subscription.end_date, timezone.now().date() + timedelta(days=30))

    def test_updates_subscription_when_end_date_is_in_the_past(self):
        subscription = SubscriptionFactory(end_date=timezone.now().date() - timedelta(days=1))
        self.handler.update_subscription(subscription)
        subscription.refresh_from_db()

        self.assertEqual(subscription.end_date, timezone.now().date() + timedelta(days=30))

    def test_does_not_update_subscription_when_end_date_is_in_the_future(self):
        future_date = timezone.now().date() + timedelta(days=10)
        subscription = SubscriptionFactory(end_date=future_date)
        self.handler.update_subscription(subscription)
        subscription.refresh_from_db()

        self.assertEqual(subscription.end_date, future_date)

    def test_does_not_update_subscription_when_end_date_is_none(self):
        subscription = SubscriptionFactory(end_date=None)
        self.handler.update_subscription(subscription)
        subscription.refresh_from_db()

        self.assertIsNone(subscription.end_date)

    def test_update_subscription_status(self):
        subscription = SubscriptionFactory(status=SubscriptionStatusChoices.INACTIVE, end_date=timezone.now().date())
        self.handler.update_subscription(subscription)
        subscription.refresh_from_db()

        self.assertEqual(subscription.status, SubscriptionStatusChoices.ACTIVE)
