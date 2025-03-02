from unittest.mock import patch

from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from apps.payments.services.stripe_events.invoice_created import InvoiceCreatedHandler
from apps.subscriptions.factories.subscription import SubscriptionFactory


class InvoiceCreatedHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.subscription = SubscriptionFactory()
        cls.user = cls.subscription.user

    def setUp(self):
        self.data = {
            "data": {
                "object": {
                    "id": "invoice_123",
                    "customer": self.user.profile.stripe_customer_id,
                    "subscription": self.subscription.stripe_subscription_id,
                    "status": "open",
                    "hosted_invoice_url": "https://stripe.com/invoice_123",
                    "invoice_pdf": "https://stripe.com/invoice_123.pdf",
                }
            }
        }
        self.handler = InvoiceCreatedHandler(self.data)

    def test_process_valid_payment(self):
        self.handler.process()

        invoice_id = self.data.get("data", {}).get("object", {}).get("id")
        self.assertTrue(Payment.objects.filter(stripe_invoice_id=invoice_id).exists())

    @patch(
        "apps.payments.services.stripe_events.invoice_created.InvoiceCreatedHandler.create_payment"
    )
    def test_process_invalid_payment_missing_user(self, mock_create_payment):
        self.handler.data["customer"] = "cus_non_exist"

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

        invoice_id = self.data.get("data", {}).get("object", {}).get("id")
        self.assertFalse(Payment.objects.filter(stripe_invoice_id=invoice_id).exists())
        mock_create_payment.assert_not_called()

    def test_get_invoice_id(self):
        self.assertEqual(self.handler.get_invoice_id(), "invoice_123")

    def test_get_invoice_id_returns_none_if_missing(self):
        self.handler.data["id"] = None
        result = self.handler.get_invoice_id()
        self.assertIsNone(result)

    def test_get_subscription_id(self):
        subscription_id = self.handler.data.get("subscription")

        self.assertEqual(self.handler.get_subscription_id(), subscription_id)

    @patch("apps.payments.services.stripe_events.invoice_created.logger.error")
    def test_get_subscription_id_logs_error_if_missing(self, mock_logger):
        self.handler.data["subscription"] = None
        result = self.handler.get_subscription_id()

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_get_invoice_status_returns_pending_for_open(self):
        self.assertEqual(
            self.handler.get_invoice_status(), PaymentStatusChoices.PENDING.value
        )

    def test_get_invoice_status_handles_unexpected_status(self):
        self.handler.data["status"] = "unexpected_status"
        result = self.handler.get_invoice_status()
        self.assertIsNone(result)

    def test_get_invoice_status_returns_none_for_invalid_status(self):
        self.handler.data["status"] = "paid"

        self.assertIsNone(self.handler.get_invoice_status())

    @patch("apps.payments.services.stripe_events.invoice_created.logger.error")
    def test_get_invoice_status_returns_pending_for_empty_status(self, mock_logger):
        self.handler.data["status"] = ""

        self.assertEqual(
            self.handler.get_invoice_status(), PaymentStatusChoices.PENDING.value
        )
        mock_logger.assert_called_once()

    def test_get_hosted_invoice_url_returns_correct_url(self):
        hosted_invoice_url = (
            self.data.get("data", {}).get("object", {}).get("hosted_invoice_url")
        )

        self.assertEqual(self.handler.get_hosted_invoice_url(), hosted_invoice_url)

    @patch("apps.payments.services.stripe_events.invoice_created.logger.error")
    def test_get_hosted_invoice_url_logs_error_if_missing(self, mock_logger):
        self.handler.data["hosted_invoice_url"] = None
        result = self.handler.get_hosted_invoice_url()

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_get_invoice_pdf_url_returns_correct_url(self):
        invoice_pdf_url = self.data.get("data", {}).get("object", {}).get("invoice_pdf")

        self.assertEqual(self.handler.get_invoice_pdf_url(), invoice_pdf_url)

    @patch("apps.payments.services.stripe_events.invoice_created.logger.error")
    def test_get_invoice_pdf_url_logs_error_if_missing(self, mock_logger):
        self.handler.data["invoice_pdf"] = None
        result = self.handler.get_invoice_pdf_url()

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_is_valid_payment_returns_true_for_valid_data(self):
        result = self.handler.is_valid_payment(
            self.user,
            self.subscription,
            "invoice_123",
            PaymentStatusChoices.PENDING.value,
        )

        self.assertTrue(result)

    def test_is_valid_payment_returns_false_if_user_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                None, self.subscription, "invoice_123", PaymentStatusChoices.PENDING.value
            )

    def test_is_valid_payment_returns_false_if_subscription_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                self.user, None, "invoice_123", PaymentStatusChoices.PENDING.value
            )


    def test_is_valid_payment_returns_false_if_invoice_id_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                self.user, self.subscription, None, PaymentStatusChoices.PENDING.value
            )

    def test_is_valid_payment_returns_false_if_status_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                self.user, self.subscription, "invoice_123", None
            )

    def test_create_payment_creates_payment_successfully(self):
        self.handler.create_payment(
            user=self.user,
            subscription=self.subscription,
            status=PaymentStatusChoices.PENDING.value,
            invoice_id="invoice_123",
            invoice_url="https://stripe.com/invoice_123",
            invoice_pdf_url="https://stripe.com/invoice_123.pdf",
        )

        self.assertTrue(
            Payment.objects.filter(stripe_invoice_id="invoice_123").exists()
        )

    @patch("apps.payments.services.stripe_events.invoice_created.logger.critical")
    def test_is_valid_payment_logs_critical_error_if_missing_fields(self, mock_logger):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(None, None, None, None)

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_created.logger.info")
    def test_create_payment_logs_success_message(self, mock_logger):
        self.handler.create_payment(
            user=self.user,
            subscription=self.subscription,
            status=PaymentStatusChoices.PENDING.value,
            invoice_id="invoice_123",
            invoice_url="https://stripe.com/invoice_123",
            invoice_pdf_url="https://stripe.com/invoice_123.pdf",
        )

        mock_logger.assert_called_once()

    def test_invoice_creation_with_missing_subscription(self):
        self.handler.data["subscription"] = None

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

        self.assertFalse(Payment.objects.exists())

    def test_invoice_creation_with_invalid_user(self):
        self.handler.data["customer"] = "invalid_customer"

        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

        self.assertFalse(Payment.objects.exists())

    @patch("apps.payments.services.stripe_events.invoice_created.logger.critical")
    def test_invoice_creation_logs_error_for_missing_fields(self, mock_logger):
        self.handler.data["id"] = None
        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

        mock_logger.assert_called()

    def test_invoice_with_invalid_status_does_not_create_payment(self):
        self.handler.data["status"] = "invalid_status"
        with self.assertRaises(RuntimeError) as context:
            self.handler.process()

        self.assertFalse(Payment.objects.exists())
