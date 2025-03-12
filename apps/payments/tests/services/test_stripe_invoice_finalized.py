from django.test import TestCase
from unittest.mock import patch

from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.stripe_events.invoice_finalized import InvoiceFinalizedHandler


class InvoiceFinalizedHandlerTest(TestCase):

    def setUp(self):
        self.data = {
            "data": {
                "object": {
                    "id": "invoice_123",
                    "amount_due": 5000,  # 50.00 USD (assuming cents)
                    "hosted_invoice_url": "https://stripe.com/invoice_123",
                    "invoice_pdf": "https://stripe.com/invoice_123.pdf",
                }
            }
        }

        self.payment = PaymentFactory(
            stripe_invoice_id="invoice_123",
            amount=0,  # Old amount
            invoice_url="",
            invoice_pdf_url="",
        )
        self.handler = InvoiceFinalizedHandler(self.data)

    def test_process_successful_update(self):

        with patch.object(self.handler, "update_payment") as mock_update:
            self.handler.process()

        mock_update.assert_called_once_with(
            self.payment, 50.00,  # amount_due converted from cents
            "https://stripe.com/invoice_123",
            "https://stripe.com/invoice_123.pdf"
        )

    @patch("apps.payments.services.stripe_events.invoice_finalized.logger.error")
    def test_process_missing_payment(self, mock_logger):
        self.payment.delete()

        with self.assertRaises(RuntimeError):
            self.handler.process()

        mock_logger.assert_called()

    @patch("apps.payments.services.stripe_events.invoice_finalized.logger.error")
    def test_process_missing_amount_due(self, mock_logger):
        self.handler.data.pop("amount_due")

        with self.assertRaises(RuntimeError):
            self.handler.process()

        mock_logger.assert_called()

    @patch("apps.payments.services.stripe_events.invoice_finalized.logger.error")
    def test_process_missing_invoice_urls(self, mock_logger):
        self.handler.data.pop("hosted_invoice_url")
        self.handler.data.pop("invoice_pdf")

        with self.assertRaises(RuntimeError):
            self.handler.process()

        mock_logger.assert_called()

    @patch("apps.payments.services.stripe_events.invoice_finalized.logger.critical")
    def test_process_missing_all_critical_fields(self, mock_logger):
        self.handler.data = {}

        with self.assertRaises(ValueError):
            self.handler.process()

        mock_logger.assert_called()

    def test_update_payment_correctly_saves_data(self):

        self.handler.update_payment(
            self.payment,
            50.00,
            "https://stripe.com/invoice_123",
            "https://stripe.com/invoice_123.pdf"
        )

        self.payment.refresh_from_db()

        self.assertEqual(self.payment.amount, 50.00)
        self.assertEqual(self.payment.invoice_url, "https://stripe.com/invoice_123")
        self.assertEqual(self.payment.invoice_pdf_url, "https://stripe.com/invoice_123.pdf")

    def test_can_update_raises_error_on_missing_fields(self):
        with self.assertRaises(RuntimeError):
            self.handler.can_update(
                invoice_id="invoice_123",
                payment=None,
                amount=None,
                hosted_invoice_url=None,
                invoice_pdf_url=None
            )

    @patch("apps.payments.services.stripe_events.invoice_finalized.logger.critical")
    def test_logger_called_on_missing_invoice_id(self, mock_logger):
        self.handler.data.pop("id")

        with self.assertRaises(ValueError):
            self.handler.process()

        mock_logger.assert_called()
