from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.stripe_events.invoice_payment_failed import InvoicePaymentFailedHandler
from apps.subscriptions.factories.subscription import SubscriptionFactory


class InvoicePaymentFailedHandlerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.subscription = SubscriptionFactory()
        cls.user = cls.subscription.user
        cls.payment = PaymentFactory(
            subscription=cls.subscription,
            user=cls.user,
            stripe_invoice_id="invoice_123",
            amount=0,  # Old amount
            invoice_url="",
            invoice_pdf_url="",
        )

    def setUp(self):
        # Patch stripe.Invoice.retrieve globally for this class
        patcher = patch("stripe.Invoice.retrieve")
        self.mock_retrieve_invoice = patcher.start()
        self.addCleanup(patcher.stop)  # Ensures patch is removed after each test

        self.data = {
            "data": {
                "object": {
                    "id": self.payment.stripe_invoice_id,
                    "amount_due": 499,
                    "customer": self.user.profile.stripe_customer_id,
                    "subscription": self.subscription.stripe_subscription_id,
                    "billing_reason": "subscription_cycle",
                    "status": "open",
                    "hosted_invoice_url": "https://stripe.com/invoice_123",
                    "invoice_pdf": "https://stripe.com/invoice_123.pdf",
                }
            }
        }

        self.stripe_invoice_mock = MagicMock(**self.data["data"]["object"])
        self.mock_retrieve_invoice.return_value = self.stripe_invoice_mock
        self.handler = InvoicePaymentFailedHandler(self.data)

    def test_process_subscription_cycle(self):
        self.handler.process()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatusChoices.RETRYING.value)

    def test_is_subscription_cycle_true(self):
        self.assertTrue(self.handler.is_subscription_cycle("subscription_cycle"))

    def test_is_subscription_cycle_false(self):
        self.assertFalse(self.handler.is_subscription_cycle("invoice_item"))

    @patch("apps.payments.services.stripe_events.invoice_payment_failed.InvoicePaymentFailedHandler.update_payment")
    def test_process_updates_payment_for_subscription_cycle(self, mock_update_payment):
        self.handler.process()

        mock_update_payment.assert_called_once_with(self.payment)

    def test_update_payment_changes_status_to_retrying(self):
        self.handler.update_payment(self.payment)
        self.assertEqual(self.payment.status, PaymentStatusChoices.RETRYING.value)

    @patch(
        "apps.payments.services.stripe_events.invoice_payment_failed.InvoicePaymentFailedHandler.send_invoice_payment_failed_email")
    def test_process_subscription_email_payment_failed(self, mock_send_invoice_payment_failed_email):
        self.handler.process()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatusChoices.RETRYING.value)
        mock_send_invoice_payment_failed_email.assert_called_once()
